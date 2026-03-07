// SERVER COMPONENT — never "use client"
import './globals.css'
import { Toaster } from 'sonner'
import { cookies } from 'next/headers'
import Navbar from '@/components/Navbar'
import { ModalOrchestrator } from '@/components/ModalOrchestrator'
import { getCurrentUser } from '@/lib/server/api'
import { JetBrains_Mono } from "next/font/google";
import { cn } from "@/lib/utils";

const jetbrainsMono = JetBrains_Mono({subsets:['latin'],variable:'--font-mono'});

export const metadata = {
    title: 'WB Digital Sahayak | ডিজিটাল সহায়ক',
    description:
        'West Bengal government scheme eligibility checker for rural citizens — আপনার অধিকার, আপনার সুযোগ।',
    keywords: 'West Bengal, government schemes, welfare, scholarship, WB Digital Sahayak',
}

export const viewport = {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
}

export default async function RootLayout({ 
    children,
    recommendations 
}: { 
    children: React.ReactNode
    recommendations?: React.ReactNode
}) {
    const cookieStore = await cookies()
    const lang = cookieStore.get('wb_lang')?.value || 'en'
    const validLang = ['en', 'bn', 'hi'].includes(lang) ? lang : 'en'

    const user = await getCurrentUser()  // cookie-based, no waterfall

    return (
        <html lang={validLang === 'bn' ? 'bn' : validLang === 'hi' ? 'hi' : 'en'} className={cn("font-mono", jetbrainsMono.variable)}>
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
                <Navbar lang={validLang} user={user} />
                <ModalOrchestrator user={user} />
                <main>
                    {children}
                    {recommendations}
                </main>

                <footer className="bg-white border-t border-gray-200 px-5 py-6 flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="3" y1="22" x2="21" y2="22" />
                                <line x1="6" y1="18" x2="6" y2="11" />
                                <line x1="10" y1="18" x2="10" y2="11" />
                                <line x1="14" y1="18" x2="14" y2="11" />
                                <line x1="18" y1="18" x2="18" y2="11" />
                                <polygon points="12 2 20 7 4 7" />
                            </svg>
                        </div>
                        <span className="text-sm text-gray-500">
                            © 2024 WB Digital Sahayak. Government of West Bengal.
                        </span>
                    </div>
                    <div className="flex gap-5">
                        <a href="#" className="text-sm text-gray-500 hover:text-blue-600 transition-colors no-underline">Privacy Policy</a>
                        <a href="#" className="text-sm text-gray-500 hover:text-blue-600 transition-colors no-underline">Terms of Service</a>
                        <a href="#" className="text-sm text-gray-500 hover:text-blue-600 transition-colors no-underline">Help Center</a>
                    </div>
                </footer>

                <Toaster
                    position="bottom-center"
                    richColors
                    closeButton
                    toastOptions={{
                        duration: 4000,
                        style: { fontFamily: 'Inter, sans-serif', fontSize: '14px' },
                    }}
                />
            </body>
        </html>
    )
}
