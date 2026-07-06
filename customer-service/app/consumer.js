const amqp = require('amqplib');
const { Pool } = require('pg');

// Reuse your database connection string
const poolCommand = new Pool({ connectionString: process.env.DATABASE_WRITE_URL });
const poolQuery = new Pool({ connectionString: process.env.DATABASE_READ_URL });
const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://admin:admin_password@rabbitmq:5672/';

async function startExcelConsumer() {
    try {
        const connection = await amqp.connect(RABBITMQ_URL);
        const channel = await connection.createChannel();

        const exchangeName = 'excel_data_exchange';
        const queueName = 'customer_service_excel_queue';

        // Ensure infrastructure topology matches the publisher matrix
        await channel.assertExchange(exchangeName, 'topic', { durable: true });
        await channel.assertQueue(queueName, { durable: true });
        await channel.bindQueue(queueName, exchangeName, 'excel.customer-service.*');

        console.log(`[EIP Consumer] Worker thread successfully bound to excel.customer-service.*`);

        channel.consume(queueName, async (msg) => {
            if (msg !== null) {
                try {
                    const ticket = JSON.parse(msg.content.toString());
                    console.log(`[EIP Consumer] Syncing raw payload record: "${ticket.topic}"`);

                    // Write to Command DB
                    const insertCommandQuery = `
                        INSERT INTO customer_service (topic, body, user_id, responses)
                        VALUES ($1, $2, $3, $4::jsonb)
                        ON CONFLICT DO NOTHING
                        RETURNING id;
                    `;

                    const result = await poolCommand.query(insertCommandQuery, [
                        ticket.topic,
                        ticket.body,
                        ticket.user_id,
                        JSON.stringify(ticket.responses || [])
                    ]);

                    // If a new row was inserted, sync it to Query DB with the same ID
                    if (result.rows.length > 0) {
                        const generatedId = result.rows[0].id;
                        const insertQueryQuery = `
                            INSERT INTO customer_service (id, topic, body, user_id, responses)
                            VALUES ($1, $2, $3, $4, $5::jsonb)
                            ON CONFLICT DO NOTHING;
                        `;
                        await poolQuery.query(insertQueryQuery, [
                            generatedId,
                            ticket.topic,
                            ticket.body,
                            ticket.user_id,
                            JSON.stringify(ticket.responses || [])
                        ]);
                    }

                    // Remove successfully stored object from RabbitMQ broker stack
                    channel.ack(msg);
                } catch (err) {
                    console.error("[EIP Consumer] Message processing exception fallback loop:", err);
                    channel.nack(msg, false, true); // Requeue message for safety
                }
            }
        });

    } catch (error) {
        console.error("[EIP Consumer] Connection to RabbitMQ broker broken. Re-polling in 5s...", error);
        setTimeout(startExcelConsumer, 5000);
    }
}

module.exports = { startExcelConsumer };