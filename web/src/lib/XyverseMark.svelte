<script lang="ts">
  // Logo pixel resmi XyVerse (assets/xyverse-icon.svg di repo profil xykalnotkel).
  let { size = 16 }: { size?: number } = $props();
  const px: [number, number, number, number][] = [
    [10, 2, 4, 2], [8, 4, 2, 2], [14, 4, 2, 2], [6, 6, 2, 2], [16, 6, 2, 2], [4, 8, 2, 2], [18, 8, 2, 2],
    [4, 10, 2, 2], [18, 10, 2, 2], [4, 12, 2, 2], [18, 12, 2, 2], [6, 14, 2, 2], [16, 14, 2, 2],
    [8, 16, 2, 2], [14, 16, 2, 2], [10, 18, 4, 2],
  ];
</script>

<svg width={size} height={size} viewBox="0 0 24 24" aria-label="XyVerse" role="img" shape-rendering="crispEdges">
  <g fill="#a78bda">
    {#each px as [x, y, w, h] (`${x}-${y}`)}
      <rect {x} {y} width={w} height={h} />
    {/each}
  </g>
</svg>
