const { StringDecoder } = require('string_decoder');
const { Pool } = require('pg');

const poolCommand = new Pool({
    connectionString: process.env.DATABASE_WRITE_URL,
});

const poolQuery = new Pool({
    connectionString: process.env.DATABASE_READ_URL,
});

// Helper function to extract and parse JSON body payload from native HTTP streams
function getRequestBody(req) {
    return new Promise((resolve, reject) => {
        const decoder = new StringDecoder('utf-8');
        let buffer = '';
        req.on('data', (chunk) => { buffer += decoder.write(chunk); });
        req.on('end', () => {
            buffer += decoder.end();
            try {
                resolve(buffer ? JSON.parse(buffer) : {});
            } catch (err) {
                reject(new Error("Invalid JSON format"));
            }
        });
    });
}

async function handleRoutes(req, res) {
    const { method, url } = req;
    res.setHeader('Content-Type', 'application/json');

    try {
        // --- 1. POST /customer-service (Create Ticket) ---
        if (url === '/customer-service' && method === 'POST') {
            const { topic, body, user_id } = await getRequestBody(req);
            if (!topic || !body || !user_id) {
                res.statusCode = 400;
                return res.end(JSON.stringify({ error: "Missing topic, body, or user_id" }));
            }

            const result = await poolCommand.query(
                `INSERT INTO customer_service (topic, body, user_id, responses) 
                 VALUES ($1, $2, $3, '[]'::jsonb) RETURNING *`,
                [topic, body, user_id]
            );

            // Synchronize with the Query DB immediately using the generated ID
            await poolQuery.query(
                `INSERT INTO customer_service (id, topic, body, user_id, responses) 
                 VALUES ($1, $2, $3, $4, '[]'::jsonb) ON CONFLICT DO NOTHING`,
                [result.rows[0].id, topic, body, user_id]
            );

            res.statusCode = 201;
            return res.end(JSON.stringify(result.rows[0]));
        }

        // --- 2. GET /customer-service (Get All Tickets) ---
        if (url === '/customer-service' && method === 'GET') {
            const result = await poolQuery.query('SELECT * FROM customer_service ORDER BY id DESC');
            res.statusCode = 200;
            return res.end(JSON.stringify(result.rows));
        }

        // Regex helpers to extract IDs from paths like /customer-service/12
        const ticketIdMatch = url.match(/^\/customer-service\/(\d+)$/);
        const responseIdMatch = url.match(/^\/customer-service\/(\d+)\/responses$/);

        // --- 3. GET /customer-service/:id (Get Ticket By ID) ---
        if (ticketIdMatch && method === 'GET') {
            const id = ticketIdMatch[1];
            const result = await poolQuery.query('SELECT * FROM customer_service WHERE id = $1', [id]);

            if (result.rows.length === 0) {
                res.statusCode = 404;
                return res.end(JSON.stringify({ error: `Ticket with ID ${id} not found` }));
            }
            res.statusCode = 200;
            return res.end(JSON.stringify(result.rows[0]));
        }

        // --- 4. DELETE /customer-service/:id (Delete Ticket By ID) ---
        if (ticketIdMatch && method === 'DELETE') {
            const id = ticketIdMatch[1];
            const result = await poolCommand.query('DELETE FROM customer_service WHERE id = $1 RETURNING id', [id]);

            if (result.rows.length === 0) {
                res.statusCode = 404;
                return res.end(JSON.stringify({ error: `Ticket with ID ${id} not found` }));
            }

            // Sync deletion to Query DB
            await poolQuery.query('DELETE FROM customer_service WHERE id = $1', [id]);

            res.statusCode = 200;
            return res.end(JSON.stringify({ message: `Ticket ${id} successfully deleted` }));
        }

        // --- 5. POST /customer-service/:id/responses (Add Response to Ticket) ---
        if (responseIdMatch && method === 'POST') {
            const id = responseIdMatch[1];
            const { responder_id, message } = await getRequestBody(req);

            if (!responder_id || !message) {
                res.statusCode = 400;
                return res.end(JSON.stringify({ error: "Missing responder_id or message" }));
            }

            // Build our atomic nested response entry
            const responseEntry = {
                responder_id,
                message,
                created_at: new Date().toISOString()
            };

            // Inject the entry dynamically onto the existing JSONB array in Command DB
            const result = await poolCommand.query(
                `UPDATE customer_service 
                 SET responses = responses || $1::jsonb 
                 WHERE id = $2 
                 RETURNING *`,
                [JSON.stringify([responseEntry]), id]
            );

            if (result.rows.length === 0) {
                res.statusCode = 404;
                return res.end(JSON.stringify({ error: `Ticket with ID ${id} not found` }));
            }

            // Sync response addition to Query DB
            await poolQuery.query(
                `UPDATE customer_service 
                 SET responses = responses || $1::jsonb 
                 WHERE id = $2`,
                [JSON.stringify([responseEntry]), id]
            );

            if (result.rows.length === 0) {
                res.statusCode = 404;
                return res.end(JSON.stringify({ error: `Ticket with ID ${id} not found` }));
            }

            res.statusCode = 201;
            return res.end(JSON.stringify({
                message: "Response appended successfully!",
                updated_ticket: result.rows[0]
            }));
        }

        // Catch-all route handler fallback
        res.statusCode = 404;
        return res.end(JSON.stringify({ error: "Endpoint route or method mismatch" }));

    } catch (error) {
        console.error("Route handling failure:", error);
        res.statusCode = error.message === "Invalid JSON format" ? 400 : 500;
        return res.end(JSON.stringify({ error: error.message || "Internal server error" }));
    }
}

module.exports = { handleRoutes };