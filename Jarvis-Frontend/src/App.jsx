import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import JarvisUI from './jarvis/jarvis_uicomponent'


// Dans ton composant


function App() {
  const [count, setCount] = useState(0)

  return (
    <>
     
      <JarvisUI/>
    </>
  )
}

export default App
