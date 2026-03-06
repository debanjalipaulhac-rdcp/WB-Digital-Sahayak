import './globals.css'
import { cookies } from 'next/headers'
import Navbar from '@/components/Navbar'
import { AuthProvider } from '@/context/AuthContext'

export const metadata = {
    title: 'WB Digital Sahayak | ডিজিটাল সহায়ক',
    description: 'West Bengal government scheme eligibility checker for rural citizens — আপনার অধিকার, আপনার সুযোগ।',
    keywords: 'West Bengal, government schemes, welfare, scholarship, WB Digital Sahayak',
}

export const viewport = {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
}

export default async function RootLayout({ children }) {
    const cookieStore = await cookies()
    const lang = cookieStore.get('wb_lang')?.value || 'en'
    const validLang = ['en', 'bn', 'hi'].includes(lang) ? lang : 'en'

    return (
        <html lang={validLang === 'bn' ? 'bn' : validLang === 'hi' ? 'hi' : 'en'}>
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;600;700&family=Inter:ital,opsz,wght@0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;1,14..32,400&display=swap"
                    rel="stylesheet"
                />
                <meta name="theme-color" content="#1A56DB" />
                {/* Dark mode flash prevention */}
                <script dangerouslySetInnerHTML={{
                    __html: `
          try {
            const t = localStorage.getItem('wb_theme');
            if (t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
              document.documentElement.classList.add('dark');
            }
          } catch(e) {}
        `}} />
            </head>
            <body>
                <AuthProvider>
                    <Navbar lang={validLang} />
                    <main>
                        {children}
                    </main>
                    <footer style={{
                        background: 'var(--color-surface, #fff)',
                        borderTop: '1px solid var(--color-border)',
                        padding: '24px 20px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '12px',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{
                                width: 32, height: 32,
                                background: 'var(--color-primary)',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="3" y1="22" x2="21" y2="22" />
                                    <line x1="6" y1="18" x2="6" y2="11" />
                                    <line x1="10" y1="18" x2="10" y2="11" />
                                    <line x1="14" y1="18" x2="14" y2="11" />
                                    <line x1="18" y1="18" x2="18" y2="11" />
                                    <polygon points="12 2 20 7 4 7" />
                                </svg>
                            </div>
                            <span style={{ fontSize: '13px', color: 'var(--color-muted)' }}>
                                © 2024 WB Digital Sahayak. Government of West Bengal.
                            </span>
                        </div>
                        <div style={{ display: 'flex', gap: '20px' }}>
                            <a href="#" style={{ fontSize: '13px', color: 'var(--color-muted)', textDecoration: 'none' }}>Privacy Policy</a>
                            <a href="#" style={{ fontSize: '13px', color: 'var(--color-muted)', textDecoration: 'none' }}>Terms of Service</a>
                            <a href="#" style={{ fontSize: '13px', color: 'var(--color-muted)', textDecoration: 'none' }}>Help Center</a>
                        </div>
                    </footer>
                </AuthProvider>
            </body>
        </html>
    )
}
