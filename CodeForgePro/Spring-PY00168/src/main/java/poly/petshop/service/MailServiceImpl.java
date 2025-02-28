package poly.petshop.service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

@Service("mailService")
public class MailServiceImpl implements MailService {
    @Autowired
    JavaMailSender mailSender;

    private List<MailService.Mail> queue = new ArrayList<>();

    @Override
    public void send(MailService.Mail mail) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "utf-8");

            helper.setFrom(mail.getFrom());
            helper.setReplyTo(mail.getFrom());
            helper.setTo(mail.getTo());
            if (!isNullOrEmpty(mail.getCc())) {
                helper.setCc(mail.getCc());
            }
            if (!isNullOrEmpty(mail.getBcc())) {
                helper.setBcc(mail.getBcc());
            }
            helper.setSubject(mail.getSubject());
            helper.setText(mail.getBody(), true);

            String filenames = mail.getFilenames();
            if (!isNullOrEmpty(filenames)) {
                for (String filename : filenames.split("[,;]+")) {
                    File file = new File(filename.trim());
                    helper.addAttachment(file.getName(), file);
                }
            }

            System.out.println("Sending email to: " + mail.getTo());
            mailSender.send(message);
            System.out.println("Email sent successfully to: " + mail.getTo());
        } catch (MessagingException e) {
            System.err.println("Failed to send email to " + mail.getTo() + ": " + e.getMessage());
            throw new RuntimeException(e);
        }
    }

    @Override
    public void push(MailService.Mail mail) {
        queue.add(mail);
        System.out.println("Mail added to queue: " + mail.getTo());
    }

    @Scheduled(fixedDelay = 500)
    public void run() {
        System.out.println("Scheduler running, queue size: " + queue.size());
        while (!queue.isEmpty()) {
            try {
                this.send(queue.remove(0));
            } catch (Exception e) {
                System.err.println("Scheduler error: " + e.getMessage());
                e.printStackTrace();
            }
        }
    }

    private boolean isNullOrEmpty(String text) {
        return (text == null || text.trim().isEmpty());
    }
}