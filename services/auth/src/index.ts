import Fastify from 'fastify';
import jwt from '@fastify/jwt';

const server = Fastify({ logger: true });

await server.register(jwt, {
  secret: process.env.JWT_SECRET || 'development-secret-change-in-production',
});

server.get('/health', async () => ({ status: 'ok' }));

server.post('/register', async (request, reply) => {
  // TODO: Implement user registration
  return reply.code(501).send({ error: 'Not implemented' });
});

server.post('/login', async (request, reply) => {
  // TODO: Implement login
  return reply.code(501).send({ error: 'Not implemented' });
});

server.get('/me', async (request, reply) => {
  // TODO: Get current user from token
  return reply.code(501).send({ error: 'Not implemented' });
});

const port = parseInt(process.env.PORT || '8001');

try {
  await server.listen({ port, host: '0.0.0.0' });
  console.log(`Auth service running on port ${port}`);
} catch (err) {
  server.log.error(err);
  process.exit(1);
}
