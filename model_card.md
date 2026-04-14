# Model Card: Music Recommender Simulation

## 1. Model Name

**MusicVibes 1.0**

A lightweight song recommender that matches your vibe to a small catalog using mood, genre, and energy.

---

## 2. Intended Use

MusicVibes 1.0 is designed to suggest songs from a 15-track catalog based on what a user says they're in the mood for. You give it a genre, a mood, and how high-energy and positive you want the music to feel, and it ranks every song and returns the top five.

It is built for classroom exploration — not for real users or production. The catalog is too small, the matching is too simple, and it makes no attempt to learn from listening history. It should not be used to make decisions about what music gets promoted or surfaced to real people.

---

## 3. How the Model Works

Every song in the catalog gets a score from 0 to 14 based on how closely it matches the user's preferences. There are four things being compared:

- **Mood** — if the song's mood matches yours exactly, it gets 4 points. If not, zero.
- **Genre** — same idea, worth 2 points for an exact match.
- **Energy** — the closer the song's energy level is to yours, the more points it earns. Very close gets 6 points, somewhat close gets 4 or 2, and far away gets nothing.
- **Valence** (positivity) — same tiered approach, worth up to 2 points.

Once every song has a score, they get sorted from highest to lowest and the top five are returned. That's the whole thing — no learning, no history, just a point system applied to a list.

---

## 4. Data

The catalog has 15 songs across 12 genres and 11 distinct moods. Each song has an energy level and a valence score between 0 and 1. The data was written manually for this project — it does not come from a real streaming service.

The catalog skews toward certain tastes: three songs are lofi, two are pop, and the "chill" mood appears three times. Most other genres and moods appear only once. There are almost no mid-energy songs — the catalog clusters around either very calm (energy 0.15–0.42) or very high-energy (0.75–0.96), with only one song in between. Dark or negative-sounding tracks are also rare — only one song has a genuinely low valence score.

---

## 5. Strengths

The system works best when the user's taste matches a well-represented part of the catalog. Lofi/chill and high-energy pop both produced clean, intuitive top-5 results where each song made sense in the ranking.

It is also fully transparent — every recommendation comes with an explanation of exactly why each song scored what it did. You can see whether a song made it because of a mood match, energy proximity, or both. That kind of explainability is something real recommenders often hide.

---

## 6. Limitations and Bias

One of the clearest weaknesses discovered during testing is what we called the "niche mood cliff" — users whose preferred mood appears only once in the catalog receive one strong recommendation and then an immediate collapse in quality. For example, a user who prefers a romantic, melancholic, or peaceful mood gets a perfect-scoring top result, but their second through fifth recommendations score less than half the maximum, chosen almost entirely by energy proximity rather than any real taste match. This stands in sharp contrast to a chill or intense user, whose mood appears two or three times in the catalog and produces a smooth, meaningful ranking across all five results. The root cause is that the scoring system has no way to signal catalog sparsity — it always returns five results even when only one genuinely fits, making the recommendations look confident when they are mostly noise. In a real product this would create a frustrating and potentially unfair experience where minority taste profiles receive the appearance of personalization without any of its actual value.

---

## 7. Evaluation

**Profiles tested**

Six user profiles were run through the system — three standard and three adversarial.

Standard profiles:
- **Chill Lofi** — lofi / chill / energy 0.38 / valence 0.58
- **High-Energy Pop** — pop / intense / energy 0.90 / valence 0.75
- **Deep Intense Rock** — rock / intense / energy 0.92 / valence 0.42

Adversarial profiles (designed to expose weaknesses):
- **Impossible Combo** — lofi / angry / energy 0.95 / valence 0.15
- **Ghost Genre** — country / chill / energy 0.35 / valence 0.65 (country is not in the catalog)
- **Dead Center** — zydeco / ethereal / energy 0.50 / valence 0.50 (neither label exists in the catalog)

---

**Chill Lofi vs High-Energy Pop**

Both profiles produced a strong, expected #1 result. Chill Lofi's top five stayed stylistically coherent all the way down — each song made some kind of sense. High-Energy Pop's list held up through #3 (Gym Hero, Sunrise City, Storm Runner) but the logic behind #3 was revealing: Storm Runner scored high because it matched the "intense" mood, even though it's a rock song and the user asked for pop. The mood weight carried it above songs that were closer in genre. That makes sense mathematically, but it's the kind of result a real user might find surprising.

---

**Deep Intense Rock vs Impossible Combo**

These two profiles are the most instructive pair. Deep Intense Rock worked exactly as intended — Storm Runner was a perfect 14/14 match and the ranking below it was clean. Impossible Combo was deliberately broken: the user asked for lofi (calm genre) but angry mood and very high energy. The result was that Iron Abyss, a metal track, landed at #1. The mood label "angry" (+4 points) completely overrode the lofi genre preference (+2 points). This confirmed that mood carries more weight than genre in the current system, and that conflicting preferences don't get averaged out — they get won by whichever feature has the higher point value.

---

**Ghost Genre vs Dead Center**

Ghost Genre (country, not in catalog) still produced reasonable results because the mood "chill" was well-represented and energy was close enough on several tracks. The system quietly dropped the genre preference and fell back on what it could match. Dead Center (both labels missing) was the most extreme case — with no categorical matches at all, the entire top five was decided by which songs happened to sit closest to 0.50 energy and 0.50 valence. The scores were so flat (8, 8, 6, 6, 5 out of 14) that the ranking was barely meaningful. The system had no way to say "I don't have enough information" — it just returned five songs anyway.

---

**What we looked for**

For each profile, we checked whether the top result made intuitive sense, whether the score gap between #1 and #5 reflected real differences in fit, and whether the reason strings matched the math. All scores were verified manually before running.

---

**What surprised us**

The most surprising result was how confident the output looked even when it was essentially guessing. Dead Center returned five songs with clean formatting and scores, but none of those results actually reflected the user's taste — there was no taste to match. A real user would have no way to know the system had nothing to offer them.

---

## 8. Future Work

**Fuzzy genre and mood matching** — right now "pop" and "indie pop" are treated as completely unrelated. A simple similarity list (or even a parent/child tag system) would let the system surface related genres instead of silently ignoring them.

**Catalog confidence signal** — the system should be able to say when it doesn't have enough matching songs. If fewer than two songs earn more than half the max score, the output could include a note like "limited matches for this taste profile" rather than padding the list with low-quality results.

**More songs, especially in the gaps** — the mid-energy range (0.45–0.70) has one song. Adding five or six tracks there would immediately improve recommendations for the largest group of users who don't want music that is either extremely calm or extremely intense.

---

## 9. Personal Reflection

The biggest learning moment in this project was realizing how much a small catalog can undermine an otherwise reasonable scoring system. The math was correct, the logic made sense, but the recommendations were sometimes misleading just because there weren't enough songs to match certain tastes. That gap between "technically working" and "actually useful" is something that doesn't show up until you run real profiles through it.

AI tools helped speed up the analysis — especially when checking expected scores across all fifteen songs for a new profile. But we still had to verify the math by hand before trusting the output, and a few early assumptions about tie-breaking and tier boundaries turned out to be wrong until we traced through specific examples.

What surprised me most was how much the results could "feel" like real recommendations even when they weren't. The formatting, the reason strings, the ranked list — it all looks legitimate. But a user who likes country music would get five lofi songs with no explanation, and it would look exactly the same as a result that genuinely matched their taste. That taught me something real about how easy it is for a system to look smart while actually just being confident.

If this project continued, the first thing I would do is expand the catalog. Not to make the algorithm smarter, but because no amount of scoring logic fixes a dataset that doesn't represent the people using it.
