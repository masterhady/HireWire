// Mock data
const results = [
  {
    username: "UserA",
    stats: {
      total_solved: 100,
      submission_calendar: {
        "1733011200": 10 // Dec 1, 2024 (10 submissions)
      }
    }
  },
  {
    username: "UserB",
    stats: {
      total_solved: 200,
      submission_calendar: {
        "1733011200": 5 // Dec 1, 2024 (5 submissions)
      }
    }
  }
];

// Helper function (copied from implementation)
const getSolvedCount = (result, filterMonth, filterYear) => {
  if (filterMonth === "all" || !result.stats?.submission_calendar) {
    return result.stats?.total_solved || 0;
  }

  try {
    const targetMonth = parseInt(filterMonth, 10);
    const targetYear = filterYear !== "all" ? parseInt(filterYear, 10) : null;
    let count = 0;

    Object.entries(result.stats.submission_calendar).forEach(([ts, val]) => {
      try {
        const timestamp = parseInt(ts, 10);
        if (isNaN(timestamp)) return;
        
        const date = new Date(timestamp * 1000);
        const resultMonth = date.getMonth() + 1;
        const resultYear = date.getFullYear();
        
        if (resultMonth === targetMonth) {
          if (targetYear === null || resultYear === targetYear) {
            count += typeof val === 'number' ? val : parseInt(String(val), 10) || 0;
          }
        }
      } catch (e) {
        // ignore
      }
    });
    return count;
  } catch (e) {
    return 0;
  }
};

// Test 1: No Filter (Sort by Total Solved)
console.log("--- Test 1: No Filter ---");
const sorted1 = [...results].sort((a, b) => {
  const valA = getSolvedCount(a, "all", "all");
  const valB = getSolvedCount(b, "all", "all");
  return valB - valA; // Descending
});
console.log("Order:", sorted1.map(r => r.username).join(", "));
console.log("Expected: UserB, UserA");

// Test 2: Filter Dec 2024 (Sort by Monthly Solved)
console.log("\n--- Test 2: Filter Dec 2024 ---");
const sorted2 = [...results].sort((a, b) => {
  const valA = getSolvedCount(a, "12", "2024");
  const valB = getSolvedCount(b, "12", "2024");
  return valB - valA; // Descending
});
console.log("Order:", sorted2.map(r => r.username).join(", "));
console.log("Expected: UserA, UserB");
