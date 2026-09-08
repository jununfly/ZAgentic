import { createHTTPServer } from '@trpc/server/adapters/standalone';
import { applyWSSHandler } from '@trpc/server/adapters/ws';
import { WebSocketServer } from 'ws';
import { appRouter } from './router';

const server = createHTTPServer({ router: appRouter });
const wss = new WebSocketServer({ server: server.server });
applyWSSHandler({ wss, router: appRouter });

server.listen(4000);
console.log('tRPC server (HTTP + WS subscriptions) on :4000, deployed via Railway');
