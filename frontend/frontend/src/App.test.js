import { render, screen } from '@testing-library/react';
import App from './App';

test('renders student erp login heading', () => {
  render(<App />);
  const headingElement = screen.getByText(/student erp login/i);
  expect(headingElement).toBeInTheDocument();
});
