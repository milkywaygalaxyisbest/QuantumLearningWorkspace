// Which chat messages count as real questions on the profile page.
// Mirrors web/backend/question_counter.py; keep the two word lists in sync.
// A message counts when it has at least one word (2+ letters or digits) that
// is not a greeting, thanks, acknowledgement or other casual filler.

const CASUAL_WORDS = new Set([
  "accha", "acha", "achha", "afternoon", "ah", "alaikum", "alot", "alright",
  "aoa", "are", "assalam", "assalamualaikum", "awesome", "bro", "buddy", "bye",
  "care", "cool", "cya", "day", "dear", "doing", "evening", "fine",
  "friend", "gm", "good", "goodbye", "got", "great", "greetings", "haan",
  "haha", "han", "hehe", "hello", "helo", "hey", "heya", "heyy",
  "hi", "hii", "hiii", "hiya", "hm", "hmm", "how", "it",
  "jazakallah", "ji", "k", "kk", "later", "lol", "lot", "maam",
  "madam", "mam", "meherbani", "morning", "much", "nah", "nice", "night",
  "no", "nope", "noted", "oh", "ok", "okay", "okey", "okk",
  "perfect", "please", "pls", "plz", "salaam", "salam", "see", "shukria",
  "shukriya", "sir", "sis", "so", "sup", "sure", "take", "thank",
  "thanks", "thanku", "thankyou", "theek", "there", "thik", "thx", "ty",
  "tysm", "u", "uh", "um", "understood", "up", "very", "wa",
  "walaikum", "welcome", "whats", "wow", "yea", "yeah", "yep", "yes",
  "yo", "you", "yup",
]);

export function isMeaningfulQuestion(text) {
  if (typeof text !== "string") return false;
  const words = text.toLowerCase().replace(/['\u2019]/g, "").match(/[\p{L}\p{N}]+/gu) || [];
  return words.some((word) => word.length >= 2 && !CASUAL_WORDS.has(word));
}
