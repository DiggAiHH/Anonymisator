/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'node',
  silent: true,
  transform: {
    '^.+\\.ts$': ['ts-jest', { tsconfig: 'tsconfig.test.json' }],
  },
  testMatch: ['**/tests-node/**/*.test.ts'],
  clearMocks: true,
  restoreMocks: true,
};
