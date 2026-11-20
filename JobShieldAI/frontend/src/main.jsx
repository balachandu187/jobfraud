import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import './index.css'
import App from './App.jsx'

async function start() {
  let googleClientId = ''
  try {
    const response = await fetch('/api/auth/google/config')
    if (response.ok) {
      const config = await response.json()
      googleClientId = config.client_id || ''
    }
  } catch (error) {
    console.error('Unable to load Google OAuth configuration:', error)
  }

  const application = <App googleClientId={googleClientId} />
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      {googleClientId ? (
        <GoogleOAuthProvider clientId={googleClientId}>
          {application}
        </GoogleOAuthProvider>
      ) : application}
    </StrictMode>,
  )
}

start()
