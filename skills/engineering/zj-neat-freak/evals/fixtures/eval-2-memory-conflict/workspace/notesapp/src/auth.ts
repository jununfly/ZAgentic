import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isProtected = createRouteMatcher(['/notes(.*)', '/settings(.*)']);

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req)) await auth.protect();
});
