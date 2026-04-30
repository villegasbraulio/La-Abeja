import { ConciergeSection } from "./ConciergeSection";
import { EditorialSection } from "./EditorialSection";
import { ExperiencePreviewSection } from "./ExperiencePreviewSection";
import { FeaturedWines } from "./FeaturedWines";
import { HeroSection } from "./HeroSection";
import { NewsletterSection } from "./NewsletterSection";
import { StoryPreviewSection } from "./StoryPreviewSection";

export function LandingPage() {
  return (
    <div>
      <HeroSection />
      <FeaturedWines />
      <ExperiencePreviewSection />
      <StoryPreviewSection />
      <ConciergeSection />
      <EditorialSection />
      <NewsletterSection />
    </div>
  );
}
