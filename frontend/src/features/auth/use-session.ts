import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api-client";
export type User = {
  id: string;
  display_name: string;
  email: string;
  role: string;
  email_verified: boolean;
  is_demo: boolean;
  ai_provider: string;
};
export function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      try {
        return await api<User>("/auth/session");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    retry: false,
  });
}
