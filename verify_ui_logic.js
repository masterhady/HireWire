// Simulate the frontend logic
const result = {
  stats: {
    total_solved: 100,
    submission_calendar: {
      "1733011200": 5, // Dec 1, 2024
      "1733097600": 5  // Dec 2, 2024
    }
  }
};

const filterMonth = "12";
const filterYear = "2024";

if (filterMonth !== "all" && filterYear !== "all") {
  if (result.stats.submission_calendar) {
    const targetMonth = parseInt(filterMonth);
    const targetYear = parseInt(filterYear);
    let count = 0;
    Object.entries(result.stats.submission_calendar).forEach(([ts, val]) => {
      const date = new Date(parseInt(ts) * 1000);
      if (date.getMonth() + 1 === targetMonth && date.getFullYear() === targetYear) {
        count += val;
      }
    });
    console.log("Count:", count);
  } else {
    console.log("Re-analyze required");
  }
} else {
  console.log("Total Solved:", result.stats.total_solved);
}

// Simulate missing calendar
const resultMissing = {
  stats: {
    total_solved: 100
  }
};

if (filterMonth !== "all" && filterYear !== "all") {
  if (resultMissing.stats.submission_calendar) {
    console.log("Should not be here");
  } else {
    console.log("Re-analyze required (Correct for missing calendar)");
  }
}
