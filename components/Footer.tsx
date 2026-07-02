import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-gray-100 mt-16">
      <div className="max-w-6xl mx-auto px-6 py-10 grid md:grid-cols-3 gap-8 text-sm text-gray-600">
        <div>
          <div className="font-bold text-gray-900 text-lg mb-2">ScheduleLink</div>
          <p>Multi-calendar scheduling for professionals. Embed your booking page anywhere.</p>
        </div>
        <div>
          <div className="font-medium text-gray-900 mb-2">Product</div>
          <ul className="space-y-1">
            <li><Link href="/#features" className="hover:text-gray-900">Features</Link></li>
            <li><Link href="/pricing" className="hover:text-gray-900">Pricing</Link></li>
            <li><Link href="/login" className="hover:text-gray-900">Sign in</Link></li>
          </ul>
        </div>
        <div>
          <div className="font-medium text-gray-900 mb-2">Legal</div>
          <ul className="space-y-1">
            <li><Link href="/privacy" className="hover:text-gray-900">Privacy</Link></li>
            <li><Link href="/terms" className="hover:text-gray-900">Terms</Link></li>
            <li><a href="mailto:support@schedulelink.tech" className="hover:text-gray-900">Contact</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-gray-100 py-6 text-center text-xs text-gray-500">
        © {new Date().getFullYear()} Otion LLC. All rights reserved.
      </div>
    </footer>
  );
}
