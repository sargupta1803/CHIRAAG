import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import routeRoutes from './routes/routeRoutes.js'

dotenv.config()

const app = express()
const PORT = process.env.PORT || 8000

app.use(cors())
app.use(express.json())
app.use(routeRoutes)

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    message: 'CHIRAAG backend is running'
  })
})

app.listen(PORT, () => {
  console.log(`CHIRAAG backend running on http://localhost:${PORT}`)
})