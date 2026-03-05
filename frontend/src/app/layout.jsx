import './globals.css'

export const metadata = {
    title: 'WB Digital Sahayak | ডিজিটাল সহায়ক',
    description: 'West Bengal government scheme eligibility checker for rural citizens — আপনার অধিকার, আপনার সুযোগ।',
    viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
}

export default function RootLayout({ children }) {
    return (
        <html lang="bn">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <meta name="theme-color" content="#020617" />
                <meta name="color-scheme" content="dark" />
            </head>
            <body className="bg-slate-950 text-white antialiased">
                {children}
            </body>
        </html>
    )
}
