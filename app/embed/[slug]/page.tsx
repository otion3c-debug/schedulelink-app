import BookingWidget from "@/components/BookingWidget";

export const dynamic = "force-dynamic";

export default function EmbedPage({ params }: { params: { slug: string } }) {
  return (
    <main className="px-4 py-6 max-w-2xl mx-auto">
      <BookingWidget slug={params.slug} />
    </main>
  );
}
