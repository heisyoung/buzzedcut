const UPSTREAM = 'https://heisyoung--buzzed-cut-v1-web.us-east.modal.run';

export default {
  async fetch(request) {
    const incoming = new URL(request.url);
    const target = new URL(UPSTREAM);
    target.pathname = incoming.pathname;
    target.search = incoming.search;

    const headers = new Headers(request.headers);
    const origin = headers.get('Origin');
    if (origin) {
      try {
        if (new URL(origin).origin !== incoming.origin) {
          return new Response('Please use the Buzzed Cut website.', { status: 403 });
        }
      } catch {
        return new Response('Invalid request origin.', { status: 403 });
      }
      headers.set('Origin', target.origin);
    }
    headers.delete('Host');
    headers.delete('X-Forwarded-For');
    const clientIP = request.headers.get('CF-Connecting-IP');
    if (clientIP) headers.set('X-Forwarded-For', clientIP);

    try {
      const response = await fetch(new Request(target, {
        method: request.method,
        headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        redirect: 'manual',
        duplex: 'half'
      }));
      const result = new Response(response.body, response);
      const location = result.headers.get('Location');
      if (location) {
        const redirect = new URL(location, target);
        if (redirect.origin === new URL(UPSTREAM).origin) {
          redirect.protocol = incoming.protocol;
          redirect.host = incoming.host;
          result.headers.set('Location', redirect.href);
        }
      }
      return result;
    } catch {
      return new Response('The studio is reconnecting. Please try again shortly.', {
        status: 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' }
      });
    }
  }
};
