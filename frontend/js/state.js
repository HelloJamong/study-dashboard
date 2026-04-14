export const state = {
  userId: '',
  courses: [],
  pollingTimer: null,
  autoPollingTimer: null,
  currentPage: 'dashboard',
  lastPlayerStatus: '',
  autoScheduleHours: [9, 13, 18, 23],
  autoEnabled: false,
  currentTerm: '',
  selectedTerm: null,   // null = 현재 학기
  currentCourseId: '',
  currentCourseName: '',
  currentSummaryId: '',
};
