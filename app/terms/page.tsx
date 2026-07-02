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
          <p>
            Questions? Email <a className="text-primary-600" href="mailto:support@schedulelink.tech">support@schedulelink.tech</a>.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
