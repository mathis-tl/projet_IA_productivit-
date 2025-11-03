#!/bin/bash
# Simple test runner for ProductivityAI Backend

echo "🧪 Running ProductivityAI Tests..."
echo ""

# Run pytest
python -m pytest tests/ -v --tb=short

# Show summary
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed"
fi

exit $EXIT_CODE
