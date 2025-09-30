import os
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
import uuid

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        # Get database URL and ensure it's in asyncpg format (postgresql://, not postgresql+asyncpg://)
        db_url = os.getenv("DATABASE_URL", "postgresql://sdc_dev_user:sdc_dev_pass_2025@localhost:5433/sdc_dev_db")
        # Convert SQLAlchemy format to asyncpg format if needed
        if "postgresql+asyncpg://" in db_url:
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                server_settings={
                    'jit': 'off'
                }
            )

            # Create tables if they don't exist
            await self._create_tables()

            logger.info("Database connection pool initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def _create_tables(self):
        """Create database tables"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn:
            # Check if users table has extended structure (user_id, department_id columns)
            extended_users_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users'
                    AND column_name = 'user_id'
                    AND data_type = 'character varying'
                )
            """)

            if not extended_users_exists:
                # Create basic users table only if extended structure doesn't exist
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        username VARCHAR(100) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            else:
                logger.info("Extended users table structure detected - skipping basic users table creation")
            
            # Create tables with appropriate foreign key references based on users table structure
            if extended_users_exists:
                # Use user_id VARCHAR references for extended users table
                user_reference = "VARCHAR REFERENCES users(user_id)"
            else:
                # Use id UUID references for basic users table
                user_reference = "UUID REFERENCES users(id)"

            # Conversations table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id {user_reference} ON DELETE CASCADE,
                    title VARCHAR(500),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Messages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    metadata JSONB,
                    sources JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Ratings table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS message_ratings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
                    user_id {user_reference} ON DELETE CASCADE,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    feedback TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(message_id, user_id)
                );
            """)
            
            # Create indexes based on existing table structures
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);")

            # Check if messages table has created_at or timestamp column
            messages_time_column = await conn.fetchval("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'messages' AND column_name IN ('created_at', 'timestamp')
                LIMIT 1
            """)

            if messages_time_column:
                await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_messages_{messages_time_column} ON messages({messages_time_column});")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_ratings_message_id ON message_ratings(message_id);")
            
            logger.info("Database tables created successfully")
    
    async def create_user(self, username: str, email: Optional[str] = None) -> Optional[str]:
        """Create a new user and return user_id"""
        if not self.pool:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                # Check if user exists
                existing_user = await conn.fetchrow(
                    "SELECT id FROM users WHERE username = $1", username
                )
                
                if existing_user:
                    return str(existing_user['id'])
                
                # Create new user
                user_id = await conn.fetchval(
                    "INSERT INTO users (username, email) VALUES ($1, $2) RETURNING id",
                    username, email
                )
                
                return str(user_id)
                
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            return None
    
    async def get_or_create_user(self, username: str) -> Optional[str]:
        """Get existing user or create new one"""
        if not self.pool:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                # Try to get existing user
                user = await conn.fetchrow(
                    "SELECT id FROM users WHERE username = $1", username
                )
                
                if user:
                    return str(user['id'])
                
                # Create new user
                user_id = await conn.fetchval(
                    "INSERT INTO users (username) VALUES ($1) RETURNING id",
                    username
                )
                
                return str(user_id)
                
        except Exception as e:
            logger.error(f"Failed to get or create user: {str(e)}")
            return None
    
    async def create_conversation(self, user_id: str, title: str = None) -> Optional[str]:
        """Create a new conversation"""
        if not self.pool:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                conversation_id = await conn.fetchval(
                    "INSERT INTO conversations (user_id, title) VALUES ($1, $2) RETURNING id",
                    user_id, title
                )
                
                return str(conversation_id)
                
        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}")
            return None
    
    async def save_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        metadata: Dict[str, Any] = None,
        sources: List[Dict] = None
    ) -> Optional[str]:
        """Save a message to the database"""
        if not self.pool:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                message_id = await conn.fetchval(
                    """INSERT INTO messages (conversation_id, role, content, metadata, sources) 
                       VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    conversation_id, 
                    role, 
                    content,
                    json.dumps(metadata) if metadata else None,
                    json.dumps(sources) if sources else None
                )
                
                return str(message_id)
                
        except Exception as e:
            logger.error(f"Failed to save message: {str(e)}")
            return None
    
    async def get_conversations(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get user's conversations with pagination"""
        if not self.pool:
            return []
            
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT c.id, c.title, c.created_at, c.updated_at,
                              (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
                       FROM conversations c 
                       WHERE c.user_id = $1 
                       ORDER BY c.updated_at DESC 
                       LIMIT $2 OFFSET $3""",
                    user_id, limit, offset
                )
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get conversations: {str(e)}")
            return []
    
    async def get_conversations_count(self, user_id: str) -> int:
        """Get total count of user's conversations"""
        if not self.pool:
            return 0
            
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = $1",
                    user_id
                )
                
                return count or 0
                
        except Exception as e:
            logger.error(f"Failed to get conversations count: {str(e)}")
            return 0
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages for a conversation"""
        if not self.pool:
            return []
            
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT m.id, m.role, m.content, m.metadata, m.sources, m.created_at,
                              r.rating, r.feedback
                       FROM messages m
                       LEFT JOIN message_ratings r ON m.id = r.message_id
                       WHERE m.conversation_id = $1
                       ORDER BY m.created_at ASC""",
                    conversation_id
                )
                
                messages = []
                for row in rows:
                    message = dict(row)
                    # Parse JSON fields
                    if message['metadata']:
                        message['metadata'] = json.loads(message['metadata'])
                    if message['sources']:
                        message['sources'] = json.loads(message['sources'])
                    messages.append(message)
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {str(e)}")
            return []
    
    async def rate_message(
        self, 
        message_id: str, 
        user_id: str, 
        rating: int, 
        feedback: str = None
    ) -> bool:
        """Rate a message (1-5 stars)"""
        if not self.pool:
            return False
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO message_ratings (message_id, user_id, rating, feedback)
                       VALUES ($1, $2, $3, $4)
                       ON CONFLICT (message_id, user_id) 
                       DO UPDATE SET rating = EXCLUDED.rating, 
                                     feedback = EXCLUDED.feedback,
                                     created_at = CURRENT_TIMESTAMP""",
                    message_id, user_id, rating, feedback
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to rate message: {str(e)}")
            return False
    
    async def get_message_rating(self, message_id: str, user_id: str) -> Optional[Dict]:
        """Get rating for a specific message by user"""
        if not self.pool:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT rating, feedback, created_at FROM message_ratings WHERE message_id = $1 AND user_id = $2",
                    message_id, user_id
                )
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Failed to get message rating: {str(e)}")
            return None
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        if not self.pool:
            return False
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE conversations SET title = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    title, conversation_id
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update conversation title: {str(e)}")
            return False
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation (only if owned by user)"""
        if not self.pool:
            return False
            
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM conversations WHERE id = $1 AND user_id = $2",
                    conversation_id, user_id
                )
                
                return result == "DELETE 1"
                
        except Exception as e:
            logger.error(f"Failed to delete conversation: {str(e)}")
            return False
    
    # =======================================================
    # USER MANAGEMENT METHODS - Added for User Management System
    # =======================================================

    async def get_user_profiles(self, limit: int = 50, offset: int = 0, search: str = "") -> List[Dict]:
        """Get user profiles with optional search and pagination - includes department info"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                if search:
                    # Search by name, employee_number, or department
                    rows = await conn.fetch(
                        """SELECT u.user_id, u.employee_number, u.name, u.department, u.phone_number,
                                  u.email, u.position, u.is_active, u.created_at, u.last_login, u.login_count,
                                  u.department_id, d.department_name,
                                  CONCAT(u.department_id, ' : ', d.department_name) as department_info
                           FROM users u
                           LEFT JOIN departments d ON u.department_id = d.department_id
                           WHERE (u.name ILIKE $1 OR u.employee_number ILIKE $1 OR u.department ILIKE $1 OR d.department_name ILIKE $1)
                           ORDER BY u.name
                           LIMIT $2 OFFSET $3""",
                        f"%{search}%", limit, offset
                    )
                else:
                    rows = await conn.fetch(
                        """SELECT u.user_id, u.employee_number, u.name, u.department, u.phone_number,
                                  u.email, u.position, u.is_active, u.created_at, u.last_login, u.login_count,
                                  u.department_id, d.department_name,
                                  CONCAT(u.department_id, ' : ', d.department_name) as department_info
                           FROM users u
                           LEFT JOIN departments d ON u.department_id = d.department_id
                           ORDER BY u.name
                           LIMIT $1 OFFSET $2""",
                        limit, offset
                    )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get user profiles: {str(e)}")
            return []

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get specific user profile by user_id - includes department info"""
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT u.user_id, u.employee_number, u.name, u.department, u.phone_number,
                              u.email, u.position, u.is_active, u.created_at, u.updated_at,
                              u.last_login, u.login_count, u.department_id, d.department_name,
                              CONCAT(u.department_id, ' : ', d.department_name) as department_info
                       FROM users u
                       LEFT JOIN departments d ON u.department_id = d.department_id
                       WHERE u.user_id = $1""",
                    user_id
                )

                return dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get user profile: {str(e)}")
            return None

    async def get_user_statistics(self, user_id: str) -> Optional[Dict]:
        """Get user usage statistics"""
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                # Get statistics from the user_statistics view
                row = await conn.fetchrow(
                    """SELECT total_sessions, total_conversations, total_messages,
                              user_messages, ai_responses, total_uploads,
                              total_tokens_used, avg_response_time
                       FROM user_statistics
                       WHERE user_id = $1""",
                    user_id
                )

                if row:
                    return dict(row)
                else:
                    # Return default statistics if no data found
                    return {
                        'total_sessions': 0,
                        'total_conversations': 0,
                        'total_messages': 0,
                        'user_messages': 0,
                        'ai_responses': 0,
                        'total_uploads': 0,
                        'total_tokens_used': 0,
                        'avg_response_time': 0
                    }

        except Exception as e:
            logger.error(f"Failed to get user statistics: {str(e)}")
            return None

    async def update_user_login(self, user_id: str) -> bool:
        """Update user login time and count"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """UPDATE users
                       SET last_login = CURRENT_TIMESTAMP,
                           login_count = login_count + 1,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = $1""",
                    user_id
                )

                return True

        except Exception as e:
            logger.error(f"Failed to update user login: {str(e)}")
            return False

    async def get_current_mock_user(self) -> Optional[Dict]:
        """Get a random mock user for development (simulating OIDC rotation)"""
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                # Get a random user from the available mock users
                row = await conn.fetchrow(
                    """SELECT user_id, name FROM users
                       WHERE user_id IN ('11111', '22222', '33333')
                       ORDER BY RANDOM()
                       LIMIT 1"""
                )

                return dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get current mock user: {str(e)}")
            return None

    async def get_user_conversation_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get detailed conversation history for a user"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT cc.conversation_id, cc.title, cc.created_at, cc.updated_at,
                              COUNT(cm.message_id) as message_count,
                              COUNT(CASE WHEN cm.message_type = 'user' THEN 1 END) as user_message_count,
                              COUNT(CASE WHEN cm.message_type = 'assistant' THEN 1 END) as ai_response_count,
                              COALESCE(SUM(cm.tokens_used), 0) as total_tokens,
                              COALESCE(AVG(cm.response_time_ms), 0) as avg_response_time
                       FROM chat_conversations_user_mgmt cc
                       LEFT JOIN chat_messages_user_mgmt cm ON cc.conversation_id = cm.conversation_id
                       WHERE cc.user_id = $1 AND cc.is_active = true
                       GROUP BY cc.conversation_id, cc.title, cc.created_at, cc.updated_at
                       ORDER BY cc.updated_at DESC
                       LIMIT $2 OFFSET $3""",
                    user_id, limit, offset
                )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get user conversation history: {str(e)}")
            return []

    async def get_user_session_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get user session history"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT session_id, login_time, logout_time, ip_address,
                              user_agent, session_duration, is_active
                       FROM user_sessions
                       WHERE user_id = $1
                       ORDER BY login_time DESC
                       LIMIT $2 OFFSET $3""",
                    user_id, limit, offset
                )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get user session history: {str(e)}")
            return []

    # OIDC 관련 메서드들
    async def create_or_update_oidc_user(self, user_data: Dict) -> bool:
        """Create or update OIDC user in database"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO users (user_id, employee_number, name, department,
                                        phone_number, email, position, is_active,
                                        created_at, updated_at, last_login, login_count)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                       ON CONFLICT (user_id)
                       DO UPDATE SET
                           name = EXCLUDED.name,
                           department = EXCLUDED.department,
                           email = EXCLUDED.email,
                           employee_number = EXCLUDED.employee_number,
                           updated_at = EXCLUDED.updated_at,
                           last_login = EXCLUDED.last_login,
                           login_count = users.login_count + 1""",
                    user_data["user_id"],
                    user_data.get("employee_number"),
                    user_data["name"],
                    user_data.get("department"),
                    user_data.get("phone_number"),
                    user_data.get("email"),
                    user_data.get("position", "OIDC User"),
                    True,  # is_active
                    datetime.now(),  # created_at
                    datetime.now(),  # updated_at
                    datetime.now(),  # last_login
                    1  # login_count (will be incremented on conflict)
                )

                logger.info(f"OIDC user {user_data['user_id']} created/updated successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to create/update OIDC user: {str(e)}")
            return False

    async def create_user_session(self, session_data: Dict) -> bool:
        """Create a new user session record"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO user_sessions (session_id, user_id, login_time,
                                                logout_time, ip_address, user_agent,
                                                session_duration, is_active)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                    session_data["session_id"],
                    session_data["user_id"],
                    datetime.now(),  # login_time
                    session_data.get("logout_time"),
                    session_data.get("ip_address"),
                    session_data.get("user_agent"),
                    session_data.get("session_duration"),
                    session_data.get("is_active", True)
                )

                logger.info(f"User session {session_data['session_id']} created successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to create user session: {str(e)}")
            return False

    async def end_user_session(self, session_id: str) -> bool:
        """End a user session (set logout time and is_active to false)"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                # Get session info for duration calculation
                session_row = await conn.fetchrow(
                    "SELECT login_time FROM user_sessions WHERE session_id = $1",
                    session_id
                )

                if session_row:
                    login_time = session_row['login_time']
                    logout_time = datetime.now()
                    session_duration = int((logout_time - login_time).total_seconds())

                    await conn.execute(
                        """UPDATE user_sessions
                           SET logout_time = $1, session_duration = $2, is_active = false
                           WHERE session_id = $3""",
                        logout_time,
                        session_duration,
                        session_id
                    )

                    logger.info(f"User session {session_id} ended successfully")
                    return True

                return False

        except Exception as e:
            logger.error(f"Failed to end user session: {str(e)}")
            return False

    async def log_user_activity(self, user_id: str, activity_type: str, activity_data: Dict) -> bool:
        """Log user activity for OIDC users"""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                # This could be expanded to a dedicated user_activities table
                # For now, we'll use the existing conversation/message tracking

                if activity_type == "chat_message":
                    # Create conversation if it doesn't exist
                    conversation_id = activity_data.get("conversation_id", f"conv_{user_id}_{datetime.now().strftime('%Y%m%d')}")

                    await conn.execute(
                        """INSERT INTO chat_conversations_user_mgmt (conversation_id, user_id,
                                                                   created_at, updated_at, title, is_active)
                           VALUES ($1, $2, $3, $4, $5, $6)
                           ON CONFLICT (conversation_id)
                           DO UPDATE SET updated_at = EXCLUDED.updated_at""",
                        conversation_id,
                        user_id,
                        datetime.now(),
                        datetime.now(),
                        activity_data.get("title", "OIDC Chat Session"),
                        True
                    )

                    # Log the message
                    message_id = activity_data.get("message_id", f"msg_{uuid.uuid4().hex[:16]}")
                    await conn.execute(
                        """INSERT INTO chat_messages_user_mgmt (message_id, conversation_id,
                                                              user_id, message_type, content,
                                                              tokens_used, model_used, response_time_ms,
                                                              created_at, metadata)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                        message_id,
                        conversation_id,
                        user_id,
                        activity_data.get("message_type", "user"),
                        activity_data.get("content", ""),
                        activity_data.get("tokens_used", 0),
                        activity_data.get("model_used"),
                        activity_data.get("response_time_ms", 0),
                        datetime.now(),
                        json.dumps(activity_data.get("metadata", {}))
                    )

                logger.info(f"User activity logged for {user_id}: {activity_type}")
                return True

        except Exception as e:
            logger.error(f"Failed to log user activity: {str(e)}")
            return False

    # Dashboard 메트릭스 관련 메서드들
    async def get_total_users_count(self) -> int:
        """Get total number of users"""
        if not self.pool:
            return 0

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM users WHERE is_active = true")
                return row['count'] if row else 0

        except Exception as e:
            logger.error(f"Failed to get total users count: {str(e)}")
            return 0

    async def get_active_sessions_count(self) -> int:
        """Get number of active user sessions"""
        if not self.pool:
            return 0

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM user_sessions WHERE is_active = true")
                return row['count'] if row else 0

        except Exception as e:
            logger.error(f"Failed to get active sessions count: {str(e)}")
            return 0

    async def get_documents_count(self) -> int:
        """Get total number of processed documents"""
        if not self.pool:
            return 0

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM documents")
                return row['count'] if row else 0

        except Exception as e:
            logger.error(f"Failed to get documents count: {str(e)}")
            return 0

    async def get_user_activity_ranking(self, limit: int = 10, from_date: str = None, to_date: str = None, department: str = None) -> List[Dict]:
        """Get user activity ranking based on message count with optional filters"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                # Build dynamic WHERE clause
                where_conditions = ["u.is_active = true"]
                params = []
                param_count = 0

                # Add date filters
                if from_date:
                    param_count += 1
                    where_conditions.append(f"cm.created_at >= ${param_count}")
                    params.append(from_date)

                if to_date:
                    param_count += 1
                    where_conditions.append(f"cm.created_at <= ${param_count}")
                    params.append(to_date)

                # Add department filter
                if department and department != "전체":
                    param_count += 1
                    where_conditions.append(f"u.department = ${param_count}")
                    params.append(department)

                # Add limit parameter
                param_count += 1
                params.append(limit)

                where_clause = " AND ".join(where_conditions)

                query = f"""SELECT u.user_id, u.name, u.department,
                              COUNT(cm.message_id) as total_messages,
                              COUNT(CASE WHEN cm.message_type = 'user' THEN 1 END) as user_messages,
                              COUNT(CASE WHEN cm.message_type = 'assistant' THEN 1 END) as ai_responses,
                              COALESCE(SUM(cm.tokens_used), 0) as total_tokens,
                              COALESCE(AVG(cm.response_time_ms), 0) as avg_response_time,
                              MAX(cm.created_at) as last_activity
                       FROM users u
                       LEFT JOIN chat_messages_user_mgmt cm ON u.user_id = cm.user_id
                       WHERE {where_clause}
                       GROUP BY u.user_id, u.name, u.department
                       HAVING COUNT(cm.message_id) > 0
                       ORDER BY COUNT(cm.message_id) DESC
                       LIMIT ${param_count}"""

                rows = await conn.fetch(query, *params)

                return [
                    {
                        "user_id": row['user_id'],
                        "name": row['name'],
                        "department": row['department'],
                        "total_messages": row['total_messages'],
                        "user_messages": row['user_messages'],
                        "ai_responses": row['ai_responses'],
                        "total_tokens": int(row['total_tokens']),
                        "avg_response_time": round(float(row['avg_response_time']), 2),
                        "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get user activity ranking: {str(e)}")
            return []

    async def get_service_usage_stats(self) -> Dict:
        """Get service usage statistics"""
        if not self.pool:
            return {}

        try:
            async with self.pool.acquire() as conn:
                # 대화 서비스 통계
                conversation_stats = await conn.fetchrow(
                    """SELECT COUNT(DISTINCT conversation_id) as total_conversations,
                              COUNT(DISTINCT user_id) as active_users,
                              AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_conversation_duration
                       FROM chat_conversations_user_mgmt
                       WHERE created_at >= NOW() - INTERVAL '7 days'"""
                )

                # 메시지 통계
                message_stats = await conn.fetchrow(
                    """SELECT COUNT(*) as total_messages,
                              COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_messages,
                              COUNT(CASE WHEN message_type = 'assistant' THEN 1 END) as ai_responses,
                              AVG(response_time_ms) as avg_response_time
                       FROM chat_messages_user_mgmt
                       WHERE created_at >= NOW() - INTERVAL '7 days'"""
                )

                return {
                    "conversations": {
                        "total": conversation_stats['total_conversations'] if conversation_stats else 0,
                        "active_users": conversation_stats['active_users'] if conversation_stats else 0,
                        "avg_duration": round(float(conversation_stats['avg_conversation_duration'] or 0), 2)
                    },
                    "messages": {
                        "total": message_stats['total_messages'] if message_stats else 0,
                        "user_messages": message_stats['user_messages'] if message_stats else 0,
                        "ai_responses": message_stats['ai_responses'] if message_stats else 0,
                        "avg_response_time": round(float(message_stats['avg_response_time'] or 0), 2)
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get service usage stats: {str(e)}")
            return {}

    async def get_document_usage_stats(self, days: int = 7) -> Dict:
        """Get document usage statistics for the last N days"""
        if not self.pool:
            return {}

        try:
            async with self.pool.acquire() as conn:
                # 문서 처리 통계
                doc_stats = await conn.fetchrow(
                    """SELECT COUNT(*) as total_documents,
                              COUNT(DISTINCT user_id) as users_uploaded,
                              SUM(file_size) as total_size_bytes,
                              AVG(file_size) as avg_size_bytes
                       FROM documents
                       WHERE upload_time >= NOW() - INTERVAL '%d days'""" % days
                )

                # 문서 청크 통계
                chunk_stats = await conn.fetchrow(
                    """SELECT COUNT(*) as total_chunks,
                              AVG(LENGTH(content)) as avg_chunk_size
                       FROM document_chunks dc
                       JOIN documents d ON dc.document_id = d.document_id
                       WHERE d.upload_time >= NOW() - INTERVAL '%d days'""" % days
                )

                return {
                    "documents": {
                        "total_processed": doc_stats['total_documents'] if doc_stats else 0,
                        "unique_uploaders": doc_stats['users_uploaded'] if doc_stats else 0,
                        "total_size_mb": round(float(doc_stats['total_size_bytes'] or 0) / (1024 * 1024), 2),
                        "avg_size_mb": round(float(doc_stats['avg_size_bytes'] or 0) / (1024 * 1024), 2)
                    },
                    "chunks": {
                        "total_chunks": chunk_stats['total_chunks'] if chunk_stats else 0,
                        "avg_chunk_size": round(float(chunk_stats['avg_chunk_size'] or 0), 2)
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get document usage stats: {str(e)}")
            return {}

    async def get_recent_activities(self, limit: int = 20) -> List[Dict]:
        """Get recent user activities"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT u.name, u.user_id, u.department,
                              cm.message_type, cm.content, cm.created_at,
                              cm.model_used, cm.response_time_ms
                       FROM chat_messages_user_mgmt cm
                       JOIN users u ON cm.user_id = u.user_id
                       WHERE u.is_active = true
                       ORDER BY cm.created_at DESC
                       LIMIT $1""",
                    limit
                )

                return [
                    {
                        "user_name": row['name'],
                        "user_id": row['user_id'],
                        "department": row['department'],
                        "activity_type": "message",
                        "message_type": row['message_type'],
                        "content_preview": row['content'][:100] + "..." if len(row['content']) > 100 else row['content'],
                        "timestamp": row['created_at'].isoformat(),
                        "model_used": row['model_used'],
                        "response_time_ms": row['response_time_ms']
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get recent activities: {str(e)}")
            return []

    async def get_overall_user_statistics(self) -> Dict:
        """전체 사용자들에 대한 종합 통계 (집계된 요약)"""
        if not self.pool:
            return {}

        try:
            async with self.pool.acquire() as conn:
                # 전체 시스템 사용 통계
                overall_stats = await conn.fetchrow(
                    """SELECT
                        COUNT(DISTINCT u.user_id) as total_users,
                        COUNT(DISTINCT CASE WHEN us.is_active = true THEN us.user_id END) as active_users_today,
                        COUNT(DISTINCT u.department) as total_departments,
                        SUM(CASE WHEN cm.message_type = 'user' THEN 1 ELSE 0 END) as total_user_messages,
                        SUM(CASE WHEN cm.message_type = 'assistant' THEN 1 ELSE 0 END) as total_ai_responses,
                        COALESCE(SUM(cm.tokens_used), 0) as total_tokens_consumed,
                        COALESCE(AVG(cm.response_time_ms), 0) as overall_avg_response_time,
                        COUNT(DISTINCT cm.conversation_id) as total_conversations,
                        COUNT(DISTINCT DATE(cm.created_at)) as active_days
                    FROM users u
                    LEFT JOIN chat_messages_user_mgmt cm ON u.user_id = cm.user_id
                    LEFT JOIN user_sessions us ON u.user_id = us.user_id
                    WHERE u.is_active = true"""
                )

                # 최근 7일간 활동 통계
                recent_activity = await conn.fetchrow(
                    """SELECT
                        COUNT(DISTINCT cm.user_id) as active_users_week,
                        COUNT(cm.message_id) as messages_this_week,
                        COUNT(DISTINCT cm.conversation_id) as conversations_this_week
                    FROM chat_messages_user_mgmt cm
                    WHERE cm.created_at >= NOW() - INTERVAL '7 days'"""
                )

                # 부서별 통계
                department_stats = await conn.fetch(
                    """SELECT
                        u.department,
                        COUNT(DISTINCT u.user_id) as user_count,
                        COUNT(cm.message_id) as total_messages
                    FROM users u
                    LEFT JOIN chat_messages_user_mgmt cm ON u.user_id = cm.user_id
                    WHERE u.is_active = true AND u.department IS NOT NULL
                    GROUP BY u.department
                    ORDER BY user_count DESC"""
                )

                return {
                    "overall_statistics": {
                        "total_users": overall_stats['total_users'] if overall_stats else 0,
                        "active_users_today": overall_stats['active_users_today'] if overall_stats else 0,
                        "active_users_week": recent_activity['active_users_week'] if recent_activity else 0,
                        "total_departments": overall_stats['total_departments'] if overall_stats else 0,
                        "total_user_messages": overall_stats['total_user_messages'] if overall_stats else 0,
                        "total_ai_responses": overall_stats['total_ai_responses'] if overall_stats else 0,
                        "total_tokens_consumed": int(overall_stats['total_tokens_consumed']) if overall_stats else 0,
                        "overall_avg_response_time": round(float(overall_stats['overall_avg_response_time'] or 0), 2),
                        "total_conversations": overall_stats['total_conversations'] if overall_stats else 0,
                        "active_days": overall_stats['active_days'] if overall_stats else 0,
                        "messages_this_week": recent_activity['messages_this_week'] if recent_activity else 0,
                        "conversations_this_week": recent_activity['conversations_this_week'] if recent_activity else 0
                    },
                    "department_breakdown": [
                        {
                            "department": row['department'],
                            "user_count": row['user_count'],
                            "total_messages": row['total_messages']
                        }
                        for row in department_stats
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to get overall user statistics: {str(e)}")
            return {}

    async def get_departments(self) -> List[str]:
        """Get list of all departments from users table"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetch(
                    """SELECT DISTINCT department
                       FROM users
                       WHERE department IS NOT NULL
                         AND department != ''
                         AND is_active = true
                       ORDER BY department"""
                )

                # Return list of department names, with "전체" first
                departments = [row['department'] for row in result]
                return ["전체"] + departments

        except Exception as e:
            logger.error(f"Error getting departments: {str(e)}")
            # Return default departments if query fails
            return ["전체", "IT부", "기획부", "마케팅부", "영업부", "HR부"]

    async def create_sample_departments(self) -> Dict:
        """Create sample users with different departments"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                # Sample users with departments
                sample_users = [
                    ("DEV001", "김개발", "01011111111", "IT개발팀"),
                    ("DEV002", "이시스템", "01022222222", "IT개발팀"),
                    ("HR001", "박인사", "01033333333", "인사팀"),
                    ("HR002", "최관리", "01044444444", "인사팀"),
                    ("MKT001", "정마케팅", "01055555555", "마케팅팀"),
                    ("MKT002", "한홍보", "01066666666", "마케팅팀"),
                    ("SAL001", "임영업", "01077777777", "영업팀"),
                    ("SAL002", "윤고객", "01088888888", "영업팀"),
                    ("FIN001", "조재무", "01099999999", "재무팀"),
                    ("FIN002", "송회계", "01010101010", "재무팀"),
                    ("RND001", "전연구", "01012121212", "연구개발팀"),
                    ("RND002", "노개발", "01013131313", "연구개발팀"),
                    ("QUA001", "민품질", "01014141414", "품질관리팀"),
                    ("QUA002", "강검사", "01015151515", "품질관리팀"),
                    ("MGT001", "오경영", "01016161616", "경영지원팀"),
                    ("MGT002", "배전략", "01017171717", "경영지원팀")
                ]

                inserted_count = 0
                for employee_id, name, phone, department in sample_users:
                    try:
                        await conn.execute(
                            """INSERT INTO users (user_id, employee_id, name, phone, department, is_active, created_at, updated_at)
                               VALUES ($1, $2, $3, $4, $5, true, NOW(), NOW())
                               ON CONFLICT (user_id) DO UPDATE SET
                               employee_id = EXCLUDED.employee_id,
                               name = EXCLUDED.name,
                               phone = EXCLUDED.phone,
                               department = EXCLUDED.department,
                               updated_at = NOW()""",
                            employee_id, employee_id, name, phone, department
                        )
                        inserted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert user {employee_id}: {str(e)}")

                return {
                    "success": True,
                    "message": f"Sample departments created successfully",
                    "inserted_users": inserted_count,
                    "total_users": len(sample_users)
                }

        except Exception as e:
            logger.error(f"Error creating sample departments: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to create sample departments: {str(e)}"
            }

    async def get_user_login_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get user login history from user_sessions table"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                # 사용자 세션 이력 조회 (부서 정보 포함)
                rows = await conn.fetch(
                    """SELECT s.session_id, s.user_id, s.login_time, s.logout_time,
                              s.is_active, s.user_agent, s.ip_address, s.session_duration,
                              u.name, u.department_id, d.department_name,
                              CONCAT(u.department_id, ' : ', d.department_name) as department_info,
                              CASE
                                  WHEN s.logout_time IS NULL AND s.is_active = true THEN true
                                  ELSE false
                              END as is_currently_active
                       FROM user_sessions s
                       LEFT JOIN users u ON s.user_id = u.user_id
                       LEFT JOIN departments d ON u.department_id = d.department_id
                       WHERE s.user_id = $1
                       ORDER BY s.login_time DESC
                       LIMIT $2""",
                    user_id, limit
                )

                return [dict(row) for row in rows] if rows else []

        except Exception as e:
            logger.error(f"Failed to get user login history: {str(e)}")
            return []

    async def get_all_users_current_status(self, limit: int = 50, offset: int = 0, search: str = "") -> List[Dict]:
        """Get all users with their current activity status and login counts"""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                # 모든 사용자의 현재 상태 조회 (접속 이력 포함)
                base_query = """
                    SELECT u.user_id, u.employee_number, u.name, u.department, u.phone_number,
                           u.email, u.position, u.is_active, u.created_at, u.last_login,
                           COALESCE(u.login_count, 0) as login_count,
                           u.department_id, d.department_name,
                           CONCAT(u.department_id, ' : ', d.department_name) as department_info,
                           COALESCE(s.total_sessions, 0) as total_sessions,
                           COALESCE(s.active_sessions, 0) as active_sessions,
                           CASE
                               WHEN s.latest_activity > NOW() - INTERVAL '15 minutes' THEN '온라인'
                               WHEN u.last_login IS NOT NULL THEN '비활성'
                               ELSE '접속 기록 없음'
                           END as current_status,
                           s.latest_activity
                    FROM users u
                    LEFT JOIN departments d ON u.department_id = d.department_id
                    LEFT JOIN (
                        SELECT user_id,
                               COUNT(*) as total_sessions,
                               COUNT(CASE WHEN logout_time > NOW() - INTERVAL '15 minutes' THEN 1 END) as active_sessions,
                               MAX(logout_time) as latest_activity
                        FROM user_sessions
                        GROUP BY user_id
                    ) s ON u.user_id = s.user_id
                """

                if search:
                    query = base_query + """
                        WHERE (u.name ILIKE $1 OR u.employee_number ILIKE $1 OR u.department ILIKE $1 OR d.department_name ILIKE $1)
                        ORDER BY u.name
                        LIMIT $2 OFFSET $3
                    """
                    rows = await conn.fetch(query, f"%{search}%", limit, offset)
                else:
                    query = base_query + """
                        ORDER BY u.name
                        LIMIT $1 OFFSET $2
                    """
                    rows = await conn.fetch(query, limit, offset)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get users current status: {str(e)}")
            return []

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

# Global database service instance
db_service = DatabaseService()