const { createServer } = require('node:http');
const { handleRoutes } = require('./routes');
const { startExcelConsumer } = require('./consumer');
const hostname = '0.0.0.0';
const port = 3000;

const server = createServer((req, res) => {
    // Forward all application traffic into our main router
    handleRoutes(req, res);
});




const { Pool } = require('pg');
const poolCommand = new Pool({ connectionString: process.env.DATABASE_WRITE_URL });
const poolQuery = new Pool({ connectionString: process.env.DATABASE_READ_URL });

async function runDatabaseMigrations(retries = 5, delay = 2000) {
    console.log("Running database schema migrations...");
    for (let i = 0; i < retries; i++) {
        try {
            // 1. Ensure table exists in Command DB
            await poolCommand.query(`
                CREATE TABLE IF NOT EXISTS customer_service (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL,
                    user_id UUID NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            `);
            await poolCommand.query(`
                ALTER TABLE customer_service 
                ADD COLUMN IF NOT EXISTS responses JSONB DEFAULT '[]'::jsonb;
            `);

            // 2. Ensure table exists in Query DB
            await poolQuery.query(`
                CREATE TABLE IF NOT EXISTS customer_service (
                    id SERIAL PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL,
                    user_id UUID NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            `);
            await poolQuery.query(`
                ALTER TABLE customer_service 
                ADD COLUMN IF NOT EXISTS responses JSONB DEFAULT '[]'::jsonb;
            `);

            console.log("Database migrations completed successfully!");
            return;
        } catch (err) {
            console.error(`Migration attempt ${i + 1} failed:`, err.message);
            if (i < retries - 1) {
                console.log(`Retrying in ${delay / 1000}s...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            } else {
                console.error("All migration attempts failed. Starting application anyway.");
            }
        }
    }
}

// Wrap your server setup in an async block so it runs migrations first
runDatabaseMigrations().then(() => {
    startExcelConsumer();

    server.listen(port, hostname, () => {
        console.log(`Customer Service microserver listening at http://localhost:${port}/`);
    });
});