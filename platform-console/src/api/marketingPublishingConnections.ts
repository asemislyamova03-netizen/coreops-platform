import { workspaceApiFetch } from "./workspace";
import type { MarketingPublishingConnection } from "../types/marketingPublishingConnection";
import { toSafePublishingConnection } from "./marketingPublishingConnectionMap";

export {
  SAFE_PUBLISHING_CONNECTION_KEYS,
  connectionViewHasSensitiveKey,
  toSafePublishingConnection,
} from "./marketingPublishingConnectionMap";

export function listMarketingPublishingConnections(): Promise<
  MarketingPublishingConnection[]
> {
  return workspaceApiFetch<Record<string, unknown>[]>(
    "/marketing/publishing-connections",
  ).then((rows) => {
    const list = Array.isArray(rows) ? rows : [];
    return list.map((row) =>
      toSafePublishingConnection(
        row && typeof row === "object"
          ? (row as Record<string, unknown>)
          : {},
      ),
    );
  });
}
