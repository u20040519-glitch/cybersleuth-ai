import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { loadRuntimeConfig } from './services/runtimeConfig'
import './index.css'

// The API address is read from `runtime-config.js`, which is served next to
// the bundle and can be replaced without a rebuild. It is loaded before the
// first render (and without the browser cache, so a stale copy can never
// point the app at an address that no longer exists).
loadRuntimeConfig().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
})
