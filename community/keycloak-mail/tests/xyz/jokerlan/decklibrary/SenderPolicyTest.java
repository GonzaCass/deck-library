package xyz.jokerlan.decklibrary;

import java.util.HashMap;
import java.util.Map;

public final class SenderPolicyTest {
    public static void main(String[] args) {
        SenderPolicy policy = new SenderPolicy("master", "deck-library", "decklibrary@example.org", "Deck Library");
        Map<String,String> original = new HashMap<>(Map.of("from", "auth@example.org", "fromDisplayName", "Auth",
            "host", "mail.example.org", "user", "auth@example.org", "password", "test-only-secret", "starttls", "true"));
        for (String client : new String[]{null,"account","security-admin-console","other-app"})
            check(policy.apply(original,"master",client) == original, "Other clients must retain the original map");
        check(policy.apply(original,"other-realm","deck-library") == original, "Other realms retain their sender");
        Map<String,String> selected = policy.apply(original,"master","deck-library");
        check(selected != original, "Use a copy for the selected client");
        for (String key : new String[]{"from","replyTo","envelopeFrom"}) check("decklibrary@example.org".equals(selected.get(key)),key);
        for (String key : new String[]{"fromDisplayName","replyToDisplayName"}) check("Deck Library".equals(selected.get(key)),key);
        for (String key : new String[]{"host","user","password","starttls"}) check(original.get(key).equals(selected.get(key)),"Preserve SMTP "+key);
        check("auth@example.org".equals(original.get("from")), "Do not mutate the realm configuration");
        System.out.println("Sender policy: 16 assertions passed");
    }
    private static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
}
