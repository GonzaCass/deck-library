package xyz.jokerlan.decklibrary;

import org.keycloak.Config;
import org.keycloak.email.DefaultEmailSenderProviderFactory;
import org.keycloak.email.EmailSenderProvider;
import org.keycloak.models.KeycloakSession;

public final class DeckEmailSenderFactory extends DefaultEmailSenderProviderFactory {
    private SenderPolicy policy;
    @Override public void init(Config.Scope config) {
        super.init(config);
        policy = new SenderPolicy(config.get("realm", "master"), config.get("client", "deck-library"),
            config.get("from", "decklibrary@jokerlan.xyz"), config.get("display-name", "Deck Library"));
    }
    @Override public EmailSenderProvider create(KeycloakSession session) {
        return new DeckEmailSender(session, super.create(session), policy);
    }
    @Override public String getId() { return "deck-library"; }
}
