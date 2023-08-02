# create_issues

Das script braucht eine configurationsdatei `config.ini`, siehe `config.ini.example`.

Es schaut im angegebenen Maildir im `new/` Ordner der Mailbox nach neuen Mails.
Und erstellt dann ein Issue. Danach wird die Mail in Trash verschoben.

- Email Subject: Titel des Issues
- Email Body: Inhalt des Issues
- Custom Email Header Assign (optional, Komma separiert): Leuten das Issue direkt zuweisen

Noch nicht in Nutzung.
