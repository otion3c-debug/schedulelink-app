import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function TermsPage() {
  return (
    <>
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="h1">Terms of Service</h1>
        <p className="text-sm text-gray-500 mt-2">Last updated: April 30, 2026</p>
        <div className="prose mt-8 space-y-4 text-gray-700">
          <p>
            By using ScheduleLink you agree to these terms. The service is provided as-is. We aim
            for 99.9% uptime but make no guarantees. Subscriptions are billed monthly via Stripe and
            can be cancelled anytime; you keep access through the end of the period.
          </p>
          <p>
            Don&apos;t use ScheduleLink to send spam, scrape calendars, or violate Google&apos;s or
            Microsoft&apos;s terms of service. We may suspend accounts that abuse the platform.
          </p>

          <h2 className="h2 mt-8">SMS Terms</h2>
          <p>
            By providing your phone number and consenting to receive SMS messages, you agree to
            receive automated booking confirmations, reminders, and service-related messages from
            ScheduleLink. Consent is not a condition of purchase. Reply STOP to cancel or HELP for
            help. Message frequency varies based on your booking activity. Message and data rates
            may apply.
          </p>
          <p>
            ScheduleLink uses Twilio, a third-party messaging provider, to deliver SMS messages.
            Standard carrier disclaimers apply. We are not liable for delayed or undelivered
            messages.
          </p>

          <p>
            Questions? Email <a className="text-primary-600" href="mailto:support@schedulelink.tech">support@schedulelink.tech</a>.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
