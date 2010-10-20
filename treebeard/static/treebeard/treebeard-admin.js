(function($){
// Ok, let's do eeet

// This is the basic Node class, which handles UI tree operations for each 'row'
var Node = function(elem) {
    var $elem = $(elem);
    var node_id = $elem.attr('node');
    var parent_id = $elem.attr('parent');
    return {
        elem: elem,
        $elem: $elem,
        node_id: node_id,
        parent_id: node_id,
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
        }
    }
}

$(document).ready(function(){

    // Don't activate drag or collapse if GET filters are set on the page
    if ($('#has-filters').val() === "1") {
        return;
    }

    // Activate all rows and instantiate a Node for each row
    $('td.drag-handler span').addClass('active');

    $('a.collapse').click(function(){
        var node = new Node($(this).closest('tr')[0]); // send the DOM node, not jQ
        node.toggle();
        return false;
    });
});
})(django.jQuery);
