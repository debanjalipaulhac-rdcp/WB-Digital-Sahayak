import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// English
import enCommon from './locales/en/common.json'
import enDashboard from './locales/en/dashboard.json'
import enSchemes from './locales/en/schemes.json'

// Bengali
import bnCommon from './locales/bn/common.json'
import bnDashboard from './locales/bn/dashboard.json'
import bnSchemes from './locales/bn/schemes.json'

// Hindi
import hiCommon from './locales/hi/common.json'
import hiDashboard from './locales/hi/dashboard.json'
import hiSchemes from './locales/hi/schemes.json'

const resources = {
    en: {
        common: enCommon,
        dashboard: enDashboard,
        schemes: enSchemes,
    },
    bn: {
        common: bnCommon,
        dashboard: bnDashboard,
        schemes: bnSchemes,
    },
    hi: {
        common: hiCommon,
        dashboard: hiDashboard,
        schemes: hiSchemes,
    },
}

if (!i18n.isInitialized) {
    i18n.use(initReactI18next).init({
        resources,
        lng: 'en',
        fallbackLng: 'en',
        ns: ['common', 'dashboard', 'schemes'],
        defaultNS: 'common',
        interpolation: {
            escapeValue: false,
        },
    })
}

export default i18n
