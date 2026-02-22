import { createContext, useContext, useMemo, useState } from 'react'
import zh from '../locales/zh.json'
import en from '../locales/en.json'

const LanguageContext = createContext()

const LOCALES = { zh, en }

function getInitialLanguage() {
  const stored = localStorage.getItem('ui_language')
  if (stored === 'zh' || stored === 'en') return stored
  return 'zh'
}

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(getInitialLanguage)

  const setLang = (nextLang) => {
    if (nextLang !== 'zh' && nextLang !== 'en') return
    setLangState(nextLang)
    localStorage.setItem('ui_language', nextLang)
  }

  const t = useMemo(() => {
    const locale = LOCALES[lang] || LOCALES.zh
    return (key) => locale[key] || key
  }, [lang])

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}
