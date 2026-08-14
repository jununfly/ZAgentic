import type { FastifyInstance } from 'fastify';
import { randomUserCode, issueDeviceCode } from '../deviceFlow';

// OAuth 2.0 Device Authorization Grant (RFC 8628)
export async function deviceRoutes(app: FastifyInstance) {
  // 设备侧：申请 device_code + user_code
  app.post('/device/code', async (req) => {
    const { client_id } = req.body as { client_id: string };
    return issueDeviceCode(client_id, { ttl: Number(process.env.DEVICE_CODE_TTL ?? 600) });
  });

  // 设备侧：轮询换 token
  app.post('/device/token', async (req, reply) => {
    const { device_code } = req.body as { device_code: string };
    const row = await app.pg.query('SELECT status FROM device_codes WHERE device_code=$1', [device_code]);
    if (row.rows[0]?.status !== 'approved') return reply.code(400).send({ error: 'authorization_pending' });
    return { access_token: '...', token_type: 'bearer' };
  });

  // 浏览器侧：用户输入 user_code 的授权确认页
  app.get('/device/verify', async (_req, reply) => reply.view('device-verify.html'));

  // 浏览器侧：列出当前用户已授权的设备
  app.get('/device/sessions', async (req) => {
    return app.pg.query('SELECT client_id, approved_at FROM device_codes WHERE user_id=$1 AND status=$2', [
      (req as any).user.id, 'approved',
    ]);
  });
}
