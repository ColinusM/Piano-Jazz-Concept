# LLM Enrichment Issues & Super-Prompt Strategy

## Current State

**Database Stats:**
- Total YouTube videos: 193
- Videos with songs extracted: 105
- Videos with NO songs: 88
- Total song entries: 192
- Success rate: 97.4%

**Failed videos (5):** JSON parsing errors
- Les Néo-classiques
- Jeux vidéo et ambition musicale
- Dix disques sur une île déserte
- Plagiat ou influence ?
- L'inexorable déclin des musiques de dessins animés

## Critical Problems Identified

### Example: Brad Mehldau Video
**Video:** "L'art de jouer diatonique avec Hal Galper et Brad Mehldau"
- URL: https://www.youtube.com/watch?v=RMByJlNy8TA
- Song analyzed: "America The Beautiful"

**What was captured:**
- ✅ Song title: America The Beautiful
- ✅ Composer info
- ❌ Performer: Says "Étienne Guéreau" (WRONG - should be Brad Mehldau & Charlie Haden)
- ❌ Featured artists: Brad Mehldau, Charlie Haden not captured
- ❌ Context: This is an ANALYSIS video, not a performance

### Current Prompt Issues

1. **Doesn't distinguish between:**
   - Who performs IN the video (Étienne demonstrates)
   - Who performed the ORIGINAL recording being analyzed (Brad/Charlie)

2. **Ignores title context:**
   - "avec Brad Mehldau" in title not used effectively
   - Featured artists not extracted

3. **Limited metadata:**
   - Could extract much more from LLM knowledge base
   - Album names, labels, famous versions not captured

4. **Theory videos missed:**
   - 88 videos have "no songs" but many ARE analyzing songs
   - Current prompt focuses on "performed" not "analyzed"

## Questions Before Building Super-Prompt

### 1. Performer Definition
What should "performer" mean?
- **Option A:** Who plays in the YouTube video (Étienne)
- **Option B:** Who played the ORIGINAL recording being analyzed (Brad/Charlie)
- **Option C:** Both (need 2 fields: "performed_by" and "analyzed_performance_by")

### 2. Metadata Scope
What metadata should be captured?
- [ ] Artists mentioned in title/description
- [ ] Album names where songs appear
- [ ] Record labels
- [ ] Famous recordings/versions
- [ ] Musical techniques discussed
- [ ] Harmonic concepts explained
- [ ] Analysis type (performance/theory/demonstration)

### 3. Featured Artists
Should we track separately?
- Video analyzes Brad Mehldau's performance → Brad is "featured artist"
- Étienne demonstrates concepts → Étienne is "demonstrator"

### 4. Theory Videos
How to handle?
- Extract songs MENTIONED/ANALYZED even if not fully played?
- Mark video type: "performance" vs "analysis" vs "theory"?
- Include pedagogical context?

## Proposed Super-Prompt Strategy

**Multi-stage approach:**

1. **Parse title aggressively**
   - Extract ALL artist names mentioned
   - Identify "feat.", "avec", "et" patterns

2. **Parse description thoroughly**
   - Look for performer credits
   - Find album references
   - Identify analysis vs performance context

3. **Use LLM knowledge base**
   - For each song: find famous recordings
   - Get discography info
   - Add historical context

4. **Distinguish video types**
   - Performance: Étienne plays the song
   - Analysis: Étienne analyzes someone else's recording
   - Theory: Uses songs as examples
   - Demonstration: Shows techniques using song excerpts

5. **Capture multiple layers:**
   ```
   - original_artist: Who wrote/first recorded
   - analyzed_performance_by: Who's playing in the recording being analyzed
   - demonstrated_by: Who's playing in this video (Étienne)
   - featured_artists: All artists mentioned/analyzed
   - video_type: performance/analysis/theory/demonstration
   ```

## Next Steps

**Awaiting decisions on:**
1. Performer field definition
2. Metadata scope
3. Featured artist tracking
4. Theory video handling

Then craft ultimate prompt and re-run enrichment on all 193 videos.
