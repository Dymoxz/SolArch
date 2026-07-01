const { createServer } = require('node:http');
const { handleRoutes } = require('./routes');

const hostname = '0.0.0.0';
const port = 3000;

const server = createServer((req, res) => {
    // Forward all application traffic into our main router
    handleRoutes(req, res);
});

server.listen(port, hostname, () => {
    console.log(`Customer Service microserver listening at http://localhost:${port}/`);
});


const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function runDatabaseMigrations() {
    console.log("Running database schema migrations...");
    try {
        // 1. Ensure base table exists
        await pool.query(`
            CREATE TABLE IF NOT EXISTS customer_service (
                id SERIAL PRIMARY KEY,
                topic VARCHAR(255) NOT NULL,
                body TEXT NOT NULL,
                user_id UUID NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        `);

        // 2. Safely add the responses column if it doesn't exist yet
        await pool.query(`
            ALTER TABLE customer_service 
            ADD COLUMN IF NOT EXISTS responses JSONB DEFAULT '[]'::jsonb;
        `);

        console.log("Database migrations completed successfully!");
    } catch (err) {
        console.error("Migration failed, application starting anyway:", err);
    }
}

// Wrap your server setup in an async block so it runs migrations first
runDatabaseMigrations().then(() => {
    server.listen(port, hostname, () => {
        console.log(`Customer Service microserver listening at http://localhost:${port}/`);
    });
});