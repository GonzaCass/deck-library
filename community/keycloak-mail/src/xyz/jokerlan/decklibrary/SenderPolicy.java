package xyz.jokerlan.decklibrary;

import java.util.HashMap;
import java.util.Map;

/** Restricts the sender override to one configured realm and client. */
public final class SenderPolicy {
    private final String realm, client, address, name;
    public SenderPolicy(String realm, String client, String address, String name) {
        this.realm = realm; this.client = client; this.address = address; this.name = name;
    }
    public Map<String,String> apply(Map<String,String> original, String realmId, String clientId) {
        if (!realm.equals(realmId) || !client.equals(clientId)) return original;
        Map<String,String> result = new HashMap<>(original);
        result.put("from", address);
        result.put("fromDisplayName", name);
        result.put("replyTo", address);
        result.put("replyToDisplayName", name);
        result.put("envelopeFrom", address);
        return result;
    }
}
