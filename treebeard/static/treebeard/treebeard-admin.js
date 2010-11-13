(function($){
// Ok, let's do eeet

// This is the basic Node class, which handles UI tree operations for each 'row'
var Node = function(elem) {
    var $elem = $(elem);
    var node_id = $elem.attr('node');
    var parent_id = $elem.attr('parent');
    var level = parseInt($elem.attr('level'));
    var children_num = parseInt($elem.attr('children-num'));
    return {
        elem: elem,
        $elem: $elem,
        node_id: node_id,
        parent_id: parent_id,
        level: level,
        has_children: function() {
            return children_num > 0;
        },
        node_name: function() {
            // Returns the text of the node
            return $elem.find('th a:not(.collapse)').text();
        },
        is_collapsed: function() {
            return $elem.find('a.collapse').hasClass('collapsed');
        },
        children: function() {
            return $('tr[parent=' + node_id + ']');
        },
        collapse: function() {
            // For each children, hide it's childrens and so on...
            $.each(this.children(), function(){
                var node = new Node(this);
                node.collapse();
            }).hide();
            // Swicth class to set the proprt expand/collapse icon
            $elem.find('a.collapse').removeClass('expanded').addClass('collapsed');
        },
        parent_node: function() {
            // Returns a Node object of the parent
            return new Node($('tr[node=' + parent_id + ']', $elem.parent())[0]);
        },
        expand: function() {
            // Display each kid (will display in collapsed state)
            this.children().show();
            // Swicth class to set the proprt expand/collapse icon
            $elem.find('a.collapse').removeClass('collapsed').addClass('expanded');

        },
        toggle: function() {
            if (this.is_collapsed()) {
                this.expand();
            } else {
                this.collapse();
            } 
        },
        clone: function() {
            return $elem.clone();
        }
    }
}

$(document).ready(function(){

    // Don't activate drag or collapse if GET filters are set on the page
    if ($('#has-filters').val() === "1") {
        return;
    }

    $body = $('body');

    // Activate all rows for drag & drop
    // then bind mouse down event
    $('td.drag-handler span').addClass('active').bind('mousedown', function(evt) {
        $ghost = $('<div id="ghost"></div>');
        $drag_line = $('<div id="drag_line"><span></span></div>');
        $ghost.appendTo($body);
        $drag_line.appendTo($body);
        
        // Create a clone create the illusion that we're moving the node
        var node = new Node($(this).closest('tr')[0]);
        cloned_node = node.clone();

        $targetRow = null;
        as_child = false;

        // Now make the new clone move with the mouse
        $body.disableSelection().bind('mousemove', function(evt2) {
            $ghost.html(cloned_node).css({  // from FeinCMS :P
                'opacity': .8, 
                'position': 'absolute', 
                'top': evt2.pageY, 
                'left': evt2.pageX-30, 
                'width': 600 
            });
            // Iterate through all rows and see where am I moving so I can place
            // the drag line accordingly
            rowHeight = node.$elem.height();
            $('tr', node.$elem.parent()).each(function(index, element) {
                $row = $(element); 
                rtop = $row.offset().top;
                // The tooltop will display whether I'm droping the element as
                // child or sibling
                $tooltip = $drag_line.find('span');
                $tooltip.css({
                    'left': node.$elem.width() - $tooltip.width(),
                    'height': rowHeight,
                });
                node_top = node.$elem.offset().top;
                // Check if you are dragging over the same node
                if (evt2.pageY >= node_top && evt2.pageY <= node_top + rowHeight) {
                    $targetRow = null;
                    $tooltip.text('Abort');
                    $drag_line.css({
                        'top': node_top,
                        'height': rowHeight,
                        'borderWidth': 0,
                        'opacity': 0.8,
                        'backgroundColor': '#ECC'
                    });
                } else
                // Check if mouse is over this row
                if (evt2.pageY >= rtop && evt2.pageY <= rtop + rowHeight/2) {
                    // The mouse is positioned on the top half of a $row
                    $targetRow = $row;
                    as_child = false;
                    $drag_line.css({
                        'left': node.$elem.offset().left,
                        'width': node.$elem.width(),
                        'top': rtop,
                        'borderWidth': '5px',
                        'height': 0,
                        'opacity': 1
                    });
                    $tooltip.text('As Sibling');
                } else if (evt2.pageY >= rtop + rowHeight/2 && evt2.pageY <= rtop + rowHeight) {
                    // The mouse is positioned on the bottom half of a row
                    $targetRow = $row;
                    as_child = true;
                    $drag_line.css({
                        'top': rtop,
                        'left': node.$elem.offset().left,
                        'height': rowHeight,
                        'opacity': 0.4,
                        'width': node.$elem.width(),
                        'borderWidth': 0,
                        'backgroundColor': '#A0A'
                    });
                    $tooltip.text('As child');
                }
            });
        }).bind('mouseup', function() {
            if ($targetRow !== null) {
                target_node = new Node($targetRow[0]);
                if (target_node.node_id !== node.node_id) {
                    /*alert('Insert node ' + node.node_name() + ' as child of: '
                    + target_node.parent_node().node_name() + '\n and sibling of: '
                        + target_node.node_name());*/
                    // Call $.ajax so we can handle the error
                    // On Drop, make an XHR call to perform the node move
                    $.ajax({
                        url: window.MOVE_NODE_ENDPOINT,
                        type: 'POST',
                        data: {
                            node_id: node.node_id,
                            parent_id: target_node.parent_id,
                            sibling_id: target_node.node_id,
                            as_child: as_child?1:0
                        },
                        complete: function(req, status) {
                            window.location.reload(); 
                        },
                        error: function(req, status, error) {
                            // On error (!200) also reload to display
                            // the message
                            window.location.reload(); 
                        }
                    });
                }
            }
            $ghost.remove();
            $drag_line.remove();
            $body.enableSelection().unbind('mousemove').unbind('mouseup');
        }).bind('keyup', function(kbevt) {
            // Cancel drag on escape
            if (kbevt.keyCode === 27) {
                $ghost.remove();
                $drag_line.remove();
                $body.enableSelection().unbind('mousemove').unbind('mouseup');
            } 
        });
    });

    $('a.collapse').click(function(){
        var node = new Node($(this).closest('tr')[0]); // send the DOM node, not jQ
        node.toggle();
        return false;
    });
});
})(django.jQuery);
