// Crockford teaches...
if (typeof Object.create !== 'function') {
    Object.create = function (o) {
        function F() {}
        F.prototype = o;
        return new F();
    };
}

(function($){
// Ok, let's do eeet

// This is the basic Node class, which handles drag and drop for each 'row'
var Node = {
    init: function(elem) {
        this.elem = elem;
        this.$elem = $(elem);
        this.node_id = this.$elem.attr('node');
        this.parent_id = this.$elem.attr('parent');
        this.collapsed = this.$elem.find('a.collapse').hasClass('collapsed');
    },
    collapse: function() {
        // For each children, hide it's childrens and so on...
        $('tr[parent=' + this.node_id + ']').each(function(){
            var node = Object.create(Node);
            node.init(this);
            node.collapse();
        }).hide();
        this.$elem.find('a.collapse').removeClass('expanded').addClass('collapsed');
    },
    expand: function() {
        // For each children, show it's kids
        $('tr[parent=' + this.node_id + ']').show();
        this.$elem.find('a.collapse').removeClass('collapsed').addClass('expanded');

    }
};

$(document).ready(function(){
    var has_filters = $('#has-filters').val() === "1";

    // Don't activate drag if GET filters are set on the page
    if (has_filters) {
        return;
    }

    // Activate all rows and instantiate a Node for each row
    $('td.drag-handler span').addClass('active');

    $('a.collapse').click(function(){
        var node = Object.create(Node);
        node.init($(this).closest('tr'));
        if (node.collapsed) {
            node.expand();
        } else {
            node.collapse();
        }
    });
});
})(django.jQuery);
