import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import JarvisUI from './jarvis/jarvis_uicomponent'
import TTSPlayer from "./jarvis/composant/TTSPlayer";

// Dans ton composant


function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <TTSPlayer />
      <JarvisUI/>
    </>
  )
}

export default App
