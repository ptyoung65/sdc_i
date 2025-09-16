export default function CurationDashboard() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Curation Dashboard</h1>
      <div style={{
        backgroundColor: '#f0f9ff',
        border: '1px solid #3b82f6',
        borderRadius: '0.5rem',
        padding: '1rem'
      }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Service Status</h2>
        <p>✅ Curation Dashboard is running on port 3004</p>
        <p>📊 AI Curation Monitoring System</p>
        <div style={{ marginTop: '1rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 'bold' }}>Features:</h3>
          <ul style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
            <li>• Content Quality Monitoring</li>
            <li>• AI Response Analytics</li>
            <li>• Curation Performance Metrics</li>
            <li>• Real-time Dashboard</li>
          </ul>
        </div>
      </div>
      <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f3f4f6', borderRadius: '0.5rem' }}>
        <p style={{ color: '#6b7280' }}>This is a minimal dashboard setup for the Curation service.</p>
        <p style={{ color: '#6b7280', marginTop: '0.5rem' }}>Connected to Curation API at http://localhost:8006</p>
      </div>
    </div>
  );
}