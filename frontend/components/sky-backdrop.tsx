/**
 * Fixed decorative sky: three soft aurora blobs in both themes and a star
 * field that fades in at night. Purely CSS, transform-only animation, and
 * fully disabled by `prefers-reduced-motion`.
 */
export function SkyBackdrop() {
  return (
    <div className="sky-backdrop" aria-hidden="true">
      <span className="sky-backdrop__blob sky-backdrop__blob--a" />
      <span className="sky-backdrop__blob sky-backdrop__blob--b" />
      <span className="sky-backdrop__blob sky-backdrop__blob--c" />
      <span className="sky-backdrop__stars" />
    </div>
  );
}
