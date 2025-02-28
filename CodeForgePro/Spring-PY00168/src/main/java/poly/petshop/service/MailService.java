package poly.petshop.service;

public interface MailService {
    public static class Mail {
        private String from = "PetShop <tranbao13061988@gmail.com>";
        private String to;
        private String cc;
        private String bcc;
        private String subject;
        private String body;
        private String filenames;

        public Mail() {
        }

        public Mail(String to, String subject, String body) {
            this.to = to;
            this.subject = subject;
            this.body = body;
        }

        public String getFrom() {
            return from;
        }

        public void setFrom(String from) {
            this.from = from;
        }

        public String getTo() {
            return to;
        }

        public void setTo(String to) {
            this.to = to;
        }

        public String getCc() {
            return cc;
        }

        public void setCc(String cc) {
            this.cc = cc;
        }

        public String getBcc() {
            return bcc;
        }

        public void setBcc(String bcc) {
            this.bcc = bcc;
        }

        public String getSubject() {
            return subject;
        }

        public void setSubject(String subject) {
            this.subject = subject;
        }

        public String getBody() {
            return body;
        }

        public void setBody(String body) {
            this.body = body;
        }

        public String getFilenames() {
            return filenames;
        }

        public void setFilenames(String filenames) {
            this.filenames = filenames;
        }
    }

    void send(Mail mail);

    void push(Mail mail);

    default void send(String to, String subject, String body) {
        Mail mail = new Mail(to, subject, body);
        send(mail);
    }

    default void push(String to, String subject, String body) {
        push(new Mail(to, subject, body));
    }
}