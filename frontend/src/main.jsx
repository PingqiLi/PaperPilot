import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

const routerFutureFlags = {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
}
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './contexts/ThemeContext'
import { LanguageProvider } from './contexts/LanguageContext'
import { TaskProvider } from './contexts/TaskContext'
import App from './App.jsx'
import './index.css'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5,
            retry: 1,
        },
    },
})

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter future={routerFutureFlags}>
                <ThemeProvider>
                    <LanguageProvider>
                        <TaskProvider>
                            <App />
                        </TaskProvider>
                    </LanguageProvider>
                </ThemeProvider>
            </BrowserRouter>
        </QueryClientProvider>
    </React.StrictMode>,
)
