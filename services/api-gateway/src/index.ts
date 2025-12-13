import Fastify from 'fastify';
import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';

const server = Fastify({ logger: true });

await server.register(cors, {
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
});

await server.register(rateLimit, {
  max: 100,
  timeWindow: '1 minute',
});

// Health check
server.get('/health', async () => ({ status: 'ok' }));

// Service routes
server.register(
  async (app) => {
    app.all('/*', async (request, reply) => {
      // TODO: Proxy to auth service
      return reply.code(501).send({ error: 'Not implemented' });
    });
  },
  { prefix: '/auth' }
);

server.register(
  async (app) => {
    app.all('/*', async (request, reply) => {
      // TODO: Proxy to chat service
      return reply.code(501).send({ error: 'Not implemented' });
    });
  },
  { prefix: '/chat' }
);

server.register(
  async (app) => {
    app.all('/*', async (request, reply) => {
      // TODO: Proxy to knowledge service
      return reply.code(501).send({ error: 'Not implemented' });
    });
  },
  { prefix: '/knowledge' }
);

const port = parseInt(process.env.PORT || '8000');

try {
  await server.listen({ port, host: '0.0.0.0' });
  console.log(`API Gateway running on port ${port}`);
} catch (err) {
  server.log.error(err);
  process.exit(1);
}
