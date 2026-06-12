// Displays one enriched word. The action buttons are optional so the same card
// works in the History/Favorites lists (where "keep going" doesn't apply).

export default function WordCard({
  data,
  isFavorite,
  onToggleFavorite,
  onKnowThis,
  onAnother,
  busy,
}) {
  if (!data) return null;

  return (
    <article className="card">
      <header className="card-head">
        <h2 className="word">{data.word}</h2>
        {onToggleFavorite && (
          <button
            className={`star ${isFavorite ? "on" : ""}`}
            onClick={() => onToggleFavorite(data.word)}
            title={isFavorite ? "Remove favorite" : "Add favorite"}
          >
            {isFavorite ? "★" : "☆"}
          </button>
        )}
      </header>

      {data.phonetic && <p className="phonetic">{data.phonetic}</p>}
      {data.part_of_speech && <p className="pos">{data.part_of_speech}</p>}

      {data.enriched ? (
        <>
          <p className="definition">{data.definition}</p>
          {data.example && <p className="example">“{data.example}”</p>}
        </>
      ) : (
        <p className="definition muted">No definition found for this word.</p>
      )}

      {(onKnowThis || onAnother) && (
        <footer className="actions">
          {onAnother && (
            <button onClick={onAnother} disabled={busy}>
              Show me another
            </button>
          )}
          {onKnowThis && (
            <button className="primary" onClick={() => onKnowThis(data.word)} disabled={busy}>
              I know this ✓
            </button>
          )}
        </footer>
      )}
    </article>
  );
}
