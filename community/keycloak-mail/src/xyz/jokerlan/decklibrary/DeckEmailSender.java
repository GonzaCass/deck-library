package xyz.jokerlan.decklibrary;

import java.util.Map;
import org.keycloak.email.EmailException;
import org.keycloak.email.EmailSenderProvider;
import org.keycloak.models.ClientModel;
import org.keycloak.models.KeycloakContext;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.UserModel;

/** Keep Keycloak's own SMTP/TLS/authentication implementation and credentials. */
public final class DeckEmailSender implements EmailSenderProvider {
    private final KeycloakSession session;
    private final EmailSenderProvider delegate;
    private final SenderPolicy policy;
    public DeckEmailSender(KeycloakSession session, EmailSenderProvider delegate, SenderPolicy policy) {
        this.session = session; this.delegate = delegate; this.policy = policy;
    }
    private Map<String,String> configuration(Map<String,String> original) {
        KeycloakContext context = session.getContext();
        if (context == null || context.getRealm() == null) return original;
        ClientModel client = context.getClient();
        if (client == null && context.getAuthenticationSession() != null)
            client = context.getAuthenticationSession().getClient();
        return policy.apply(original, context.getRealm().getName(), client == null ? null : client.getClientId());
    }
    @Override public void send(Map<String,String> config, UserModel user, String subject, String text, String html) throws EmailException {
        delegate.send(configuration(config), user, subject, text, html);
    }
    @Override public void send(Map<String,String> config, String address, String subject, String text, String html) throws EmailException {
        delegate.send(configuration(config), address, subject, text, html);
    }
    @Override public void validate(Map<String,String> config) throws EmailException { delegate.validate(configuration(config)); }
    @Override public void close() { delegate.close(); }
}
