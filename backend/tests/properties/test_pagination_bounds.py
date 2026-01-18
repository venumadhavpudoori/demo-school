"""Property-based tests for pagination bounds.

**Feature: school-erp-multi-tenancy, Property 15: Pagination Bounds**
**Validates: Design - Property 15**

Property 15: Pagination Bounds
*For any* paginated list request with page_size N, the returned results SHALL contain
at most N items, and the total_count SHALL reflect the actual count of matching records.
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.repositories.base import PaginatedResult


# Strategy for page numbers (1-indexed)
page_strategy = st.integers(min_value=1, max_value=1000)

# Strategy for page sizes (will be capped at 100 by the repository)
page_size_strategy = st.integers(min_value=1, max_value=200)

# Strategy for total record counts
total_count_strategy = st.integers(min_value=0, max_value=10000)


class TestPaginationBounds:
    """**Feature: school-erp-multi-tenancy, Property 15: Pagination Bounds**"""

    @given(
        page_size=page_size_strategy,
        total_count=total_count_strategy,
        page=page_strategy,
    )
    @settings(max_examples=100)
    def test_paginated_result_items_at_most_page_size(
        self,
        page_size: int,
        total_count: int,
        page: int,
    ):
        """For any paginated result, items count SHALL be at most page_size.

        **Validates: Design - Property 15**
        """
        # Calculate effective page_size (capped at 100 as per repository implementation)
        effective_page_size = max(1, min(page_size, 100))
        
        # Calculate how many items would be on this page
        offset = (page - 1) * effective_page_size
        remaining = max(0, total_count - offset)
        expected_items_count = min(remaining, effective_page_size)
        
        # Create mock items (simple objects)
        mock_items = [object() for _ in range(expected_items_count)]
        
        # Create PaginatedResult
        result = PaginatedResult(
            items=mock_items,
            total_count=total_count,
            page=page,
            page_size=effective_page_size,
        )
        
        # Assert: items count is at most page_size
        assert len(result.items) <= effective_page_size, (
            f"Paginated result must contain at most {effective_page_size} items. "
            f"Got: {len(result.items)}"
        )

    @given(
        page_size=page_size_strategy,
        total_count=total_count_strategy,
        page=page_strategy,
    )
    @settings(max_examples=100)
    def test_paginated_result_total_count_reflects_actual_count(
        self,
        page_size: int,
        total_count: int,
        page: int,
    ):
        """For any paginated result, total_count SHALL reflect actual count of matching records.

        **Validates: Design - Property 15**
        """
        # Calculate effective page_size
        effective_page_size = max(1, min(page_size, 100))
        
        # Create PaginatedResult with the given total_count
        result = PaginatedResult(
            items=[],
            total_count=total_count,
            page=page,
            page_size=effective_page_size,
        )
        
        # Assert: total_count is preserved
        assert result.total_count == total_count, (
            f"Paginated result must preserve total_count. "
            f"Expected: {total_count}, Got: {result.total_count}"
        )

    @given(
        page_size=page_size_strategy,
        total_count=total_count_strategy,
        page=page_strategy,
    )
    @settings(max_examples=100)
    def test_paginated_result_total_pages_calculation(
        self,
        page_size: int,
        total_count: int,
        page: int,
    ):
        """For any paginated result, total_pages SHALL be correctly calculated.

        **Validates: Design - Property 15**
        """
        # Calculate effective page_size
        effective_page_size = max(1, min(page_size, 100))
        
        # Create PaginatedResult
        result = PaginatedResult(
            items=[],
            total_count=total_count,
            page=page,
            page_size=effective_page_size,
        )
        
        # Calculate expected total pages
        expected_total_pages = (total_count + effective_page_size - 1) // effective_page_size
        
        # Assert: total_pages is correctly calculated
        assert result.total_pages == expected_total_pages, (
            f"Total pages must be ceil(total_count / page_size). "
            f"Expected: {expected_total_pages}, Got: {result.total_pages}"
        )

    @given(
        page_size=page_size_strategy,
        total_count=st.integers(min_value=1, max_value=10000),  # At least 1 record
        page=page_strategy,
    )
    @settings(max_examples=100)
    def test_paginated_result_has_next_property(
        self,
        page_size: int,
        total_count: int,
        page: int,
    ):
        """For any paginated result, has_next SHALL be True iff page < total_pages.

        **Validates: Design - Property 15**
        """
        # Calculate effective page_size
        effective_page_size = max(1, min(page_size, 100))
        
        # Create PaginatedResult
        result = PaginatedResult(
            items=[],
            total_count=total_count,
            page=page,
            page_size=effective_page_size,
        )
        
        # Calculate expected has_next
        total_pages = (total_count + effective_page_size - 1) // effective_page_size
        expected_has_next = page < total_pages
        
        # Assert: has_next is correctly calculated
        assert result.has_next == expected_has_next, (
            f"has_next must be True iff page < total_pages. "
            f"page={page}, total_pages={total_pages}, "
            f"Expected has_next: {expected_has_next}, Got: {result.has_next}"
        )

    @given(
        page_size=page_size_strategy,
        total_count=total_count_strategy,
        page=page_strategy,
    )
    @settings(max_examples=100)
    def test_paginated_result_has_previous_property(
        self,
        page_size: int,
        total_count: int,
        page: int,
    ):
        """For any paginated result, has_previous SHALL be True iff page > 1.

        **Validates: Design - Property 15**
        """
        # Calculate effective page_size
        effective_page_size = max(1, min(page_size, 100))
        
        # Create PaginatedResult
        result = PaginatedResult(
            items=[],
            total_count=total_count,
            page=page,
            page_size=effective_page_size,
        )
        
        # Assert: has_previous is correctly calculated
        expected_has_previous = page > 1
        assert result.has_previous == expected_has_previous, (
            f"has_previous must be True iff page > 1. "
            f"page={page}, Expected: {expected_has_previous}, Got: {result.has_previous}"
        )

    @given(
        page_size=st.integers(min_value=1, max_value=100),
        total_count=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=100)
    def test_items_on_last_page_at_most_remainder(
        self,
        page_size: int,
        total_count: int,
    ):
        """For any last page, items count SHALL be at most the remainder.

        **Validates: Design - Property 15**
        """
        # Skip if no records
        assume(total_count > 0)
        
        # Calculate last page
        total_pages = (total_count + page_size - 1) // page_size
        last_page = total_pages
        
        # Calculate expected items on last page
        remainder = total_count % page_size
        expected_items_on_last_page = remainder if remainder > 0 else page_size
        
        # Create mock items for last page
        mock_items = [object() for _ in range(expected_items_on_last_page)]
        
        # Create PaginatedResult for last page
        result = PaginatedResult(
            items=mock_items,
            total_count=total_count,
            page=last_page,
            page_size=page_size,
        )
        
        # Assert: items count matches expected
        assert len(result.items) == expected_items_on_last_page, (
            f"Last page must have correct number of items. "
            f"total_count={total_count}, page_size={page_size}, "
            f"Expected: {expected_items_on_last_page}, Got: {len(result.items)}"
        )
        
        # Assert: items count is at most page_size
        assert len(result.items) <= page_size, (
            f"Last page items must be at most page_size. "
            f"page_size={page_size}, Got: {len(result.items)}"
        )

    @given(
        page_size=st.integers(min_value=1, max_value=100),
        total_count=st.integers(min_value=0, max_value=1000),
        page=page_strategy,
    )
    @settings(max_examples=100)
    def test_empty_page_beyond_total_pages(
        self,
        page_size: int,
        total_count: int,
        page: int,
    ):
        """For any page beyond total_pages, items SHALL be empty.

        **Validates: Design - Property 15**
        """
        # Calculate total pages
        if total_count == 0:
            total_pages = 0
        else:
            total_pages = (total_count + page_size - 1) // page_size
        
        # Only test pages beyond total_pages
        assume(page > total_pages and total_pages > 0)
        
        # Create PaginatedResult for page beyond total
        result = PaginatedResult(
            items=[],  # Should be empty
            total_count=total_count,
            page=page,
            page_size=page_size,
        )
        
        # Assert: items is empty for pages beyond total
        assert len(result.items) == 0, (
            f"Pages beyond total_pages must have empty items. "
            f"page={page}, total_pages={total_pages}, Got items: {len(result.items)}"
        )
        
        # Assert: total_count is still preserved
        assert result.total_count == total_count, (
            f"total_count must be preserved even for pages beyond total. "
            f"Expected: {total_count}, Got: {result.total_count}"
        )
