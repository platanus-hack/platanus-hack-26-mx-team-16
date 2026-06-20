import { jwtDecode, type JwtPayload } from "jwt-decode";

export function isTokenValid(token: string): boolean {
  try {
    const decoded = jwtDecode<JwtPayload>(token);
    if (!decoded.exp) return false;
    const currentTime = Math.floor(Date.now() / 1000);
    return decoded.exp >= currentTime;
  } catch {
    return false;
  }
}
