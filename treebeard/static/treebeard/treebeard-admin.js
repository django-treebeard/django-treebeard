(function ($) {
    MOVE_NODE_ENDPOINT = 'move/';
    GET_CHILDREN_ENDPOINT = 'children/';
    CSRF_TOKEN = document.currentScript.dataset.csrftoken;

    // Node class, handles UI tree operations for each 'row'
    class Node {
        constructor(elem) {
            this.$elem = $(elem);
            this.id = this.$elem.data('node-id');
            this.childrenLoaded = Boolean(this.$elem.data("children-loaded"));
        }

        isCollapsed() {
            return this.$elem.find('a.treebeard-collapse').hasClass('treebeard-collapsed');
        }

        children() {
            return $('tr[data-parent-id="' + this.id + '"]');
        }

        collapse() {
            // For each child, hide it's children and so on...
            $.each(this.children(), function () {
                new Node(this).collapse();
            }).hide();

            // Switch class to set the property expand/collapse icon
            this.$elem.find('a.treebeard-collapse').removeClass('treebeard-expanded').addClass('treebeard-collapsed');
        }

        expand() {
            if (this.childrenLoaded) {
                this.children().show();
                // Switch class to set the property expand/collapse icon
                this.$elem.find('a.treebeard-collapse').removeClass('treebeard-collapsed').addClass('treebeard-expanded');
            }
            else {
                this.loadChildren();
            }
        }

        toggle() {
            if (this.isCollapsed()) {
                this.expand();
            } else {
                this.collapse();
            }
        }

        loadChildren(resultList = [], contextList = [], page = 1) {
            this.$elem.attr("data-children-loaded", "1");
            this.childrenLoaded = true;
            this.$elem.find("a.treebeard-collapse").removeClass("treebeard-collapsed").addClass("treebeard-loading");
            const params = new URLSearchParams(window.location.search);
            params.set("p", page);

            $.get(`${GET_CHILDREN_ENDPOINT}${this.id}/`, params.toString()).done(response => {
                resultList.push(...$(response["result_html"]).find("#result_list tbody tr").toArray());
                contextList.push(...response["tree_context"]);

                if (response["page"] < response["num_pages"]) { // Recursively fetch all pages
                    return this.loadChildren(resultList, contextList, response["page"] + 1);
                }

                const $resultList = $(resultList);
                setupData($resultList, contextList);
                $resultList.insertAfter(this.$elem);
                this.$elem.find("a.treebeard-collapse").removeClass("treebeard-loading").addClass("treebeard-expanded");
            });
        }
    }

    const setupData = ($resultList, contextList) => {
        $resultList.each((index, el) => Object.entries(contextList[index]).forEach(
            ([key, val]) => $(el).attr(`data-${key}`, val))
        );

        // Add drag handler and spacers to each node
        $resultList.each((idx, el) => {
            const $row = $(el);
            // Inject spacer and collapse buttons into the first table cell that isn't an action checkbox or drag handler
            const $firstCell = $row.find("td,th").not(".action-checkbox").first();
            if (!$firstCell.length) {
                return;
            }

            const hasChildren = parseInt($row.data("has-children")),
                canChange = parseInt($row.data("can-change")),
                level = parseInt($row.data("level"));

            const elements = [
                canChange ? "<span class='drag-handler' draggable='true'></span>" : "<span class='drag-handler drag-handler-disabled'></span>"
            ];

            if (level > 1) {
                elements.push("<span class='spacer'>&nbsp;</span>".repeat(level - 1));
            }

            if (hasChildren) {
                elements.push("<a href='#' class='treebeard-collapse treebeard-collapsed' role='button'></a>");
            }

            $firstCell.prepend(elements);
        });
    }

    const setupDragHandler = () => {
        if ($('#has-change-permission').val() === "0") {
            return;
        }

        const $body = $('body');
        const $resultList = $("#result_list");

        let dragPageY = null;
        let draggedNode = null;
        let targetNode = null;
        let relation = "child";

        const $ghost = $('<div id="ghost"></div>');
        const $tooltip = $('<div id="drag-tooltip"></div>');
        $ghost.appendTo($body).hide();
        $tooltip.appendTo($body).hide();

        // Workaround for https://bugzilla.mozilla.org/show_bug.cgi?id=505521
        // We can't rely on the drag event on the target to identify the position of the pointer
        $body.on("dragover", event => dragPageY = event.pageY);

        // Make node rows targets for dragging
        $resultList.on("dragover", "tr", event => event.preventDefault());

        $resultList.on("dragenter", "tbody tr", (event) => {
            if (targetNode) {
                targetNode.$elem.removeClass("target-node-parent").removeClass("target-node-sibling")
            }
            targetNode = new Node($(event.currentTarget));
            if (targetNode.isCollapsed()) {
                targetNode.expand();
            }
        });

        $body.on("dragend", () => {
            if (targetNode) {
                targetNode.$elem.removeClass("target-node-parent target-node-sibling");
            }
            targetNode = null;
            draggedNode.$elem.removeClass("active-node");
            $ghost.hide();
            $tooltip.hide();
        });

        $body.on("dragstart", (event) => {
            $ghost.show();
            $tooltip.show();

            // Create a clone create the illusion that we're moving the node
            draggedNode = new Node($(event.target).closest('tr')[0]);
            draggedNode.$elem.addClass("active-node");
            $ghost.html(draggedNode.$elem.clone());

            event.originalEvent.dataTransfer.setDragImage($ghost[0], 0, 0);
        });

        $body.on("drag", (event) => {
            if (!targetNode) {
                return;
            }

            const $row = targetNode.$elem;
            const rtop = $row.offset().top;

            let text;

            if (targetNode.id == draggedNode.id) {
                text = gettext('Abort');
            } else if (dragPageY >= rtop && dragPageY <= rtop + $row.height() / 2) {
                // The mouse is positioned on the top half of a row
                relation = "sibling";
                $row.removeClass("target-node-parent").addClass("target-node-sibling");
                text = gettext('As Sibling');
            } else {
                // The mouse is positioned on the bottom half of a row
                relation = "child";
                $row.removeClass("target-node-sibling").addClass("target-node-parent");
                text = gettext('As child');
            }

            $tooltip.css({
                "left": $row.offset().left + $row.width() - $tooltip.width(),
                "top": rtop,
                'height': $row.outerHeight() - 2,
            }).text(text);
        });

        $resultList.on('drop', "tbody tr", (event) => {
            if (targetNode.id == draggedNode.id) {
                return;
            }

            // On Drop, make an XHR call to perform the node move
            $.post({
                url: MOVE_NODE_ENDPOINT,
                data: {
                    node: draggedNode.id,
                    target: targetNode.id,
                    relation: relation,
                },
                headers: {
                    "X-CSRFToken": CSRF_TOKEN
                },
            }).always(() => {
                // Reload the page even on error, so that messages are displayed
                window.location.reload();
            });
        });
    }

    $(document).ready(function () {
        const $resultList = $('#result_list tbody tr');
        const contextList = JSON.parse(document.getElementById('tree-context').textContent);

        setupData($resultList, contextList);

        $('#result_list').on("click", "a.treebeard-collapse", (event) => {
            event.preventDefault();
            new Node($(event.currentTarget).closest('tr')[0]).toggle();
        });

        setupDragHandler();
    });
})(django.jQuery);
