interface StarRatingProps {
  rating: number | null;
  count: number;
}

export function StarRating({ rating, count }: StarRatingProps) {
  if (!rating) {
    return <p className="text-sm text-burgundy-500">Todavía no tiene reseñas.</p>;
  }

  return (
    <p className="text-sm text-burgundy-700">
      {rating.toFixed(1)} / 5 · {count} reseñas
    </p>
  );
}
