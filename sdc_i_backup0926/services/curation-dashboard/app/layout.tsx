export const metadata = {
  title: 'Curation Dashboard',
  description: 'AI Curation Service Dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}