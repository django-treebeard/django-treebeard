/**
 * 
 * Nested Sortable Widget with pagination support for jQuery/Interface.
 *  
 * Version 1.0
 * 
 * Copyright (c) 2007 Bernardo de Padua dos Santos
 * Dual licensed under the MIT (MIT-LICENSE.txt) 
 * and GPL (GPL-LICENSE.txt) licenses.
 * 
 * http://code.google.com/p/nestedsortables/
 * 
 */

jQuery.NestedSortableWidget = {
	
	setBusyState : function(e, isBusy) {
		e.nestedSortWidgetCfg.busyLoading = isBusy;
		var sel = jQuery('.' + e.nestedSortWidgetCfg.classes.progress, e);
		if(isBusy) {
			sel.show();
		} else {
			sel.hide();
		}
	},
	userWarning : function(e, message) {
		var sel = jQuery('.' + e.nestedSortWidgetCfg.classes.warning, e)
			.html(message)
			.show(
				'slow',
				function() {
					setTimeout(function() {sel.hide('slow');}, '10000');
				}
			);
		
	},
	loadPage: function (e, where) {
		var curPage = e.nestedSortWidgetCfg.currentPage;
		var loadData = jQuery.NestedSortableWidget.loadData;
		var nextPage;
		switch (where) {
			case 'before':
				if(e.nestedSortWidgetCfg.incremental) {
					nextPage = e.nestedSortWidgetCfg.bottomPage - 1;
				} else {
					nextPage = curPage - 1;
				}
			break;
			case 'after':
				if(e.nestedSortWidgetCfg.incremental) {
					nextPage = e.nestedSortWidgetCfg.upperPage + 1;
				} else {
					nextPage = curPage + 1;
				}			
			break;
		}
		return loadData(e, nextPage);
	},
	loadData: function(e, page) {		
		/*
		 * PRIVATE FUNCTIONS
		 */
		
		/*
		 * Figures out what needs to be requested to the server in
		 * order to display the requested page.
		 */
		var whatToRequest = function() {
			if(e.nestedSortWidgetCfg.paginate && !e.nestedSortWidgetCfg.greedy) {
				var retVal;
				if(e.nestedSortWidgetCfg.incremental) {
					var cur;
					if(page > e.nestedSortWidgetCfg.upperPage) {
						cur = e.nestedSortWidgetCfg.upperPage;
					} else {
						cur = e.nestedSortWidgetCfg.bottomPage;
					}
					retVal = jQuery.NestedSortableWidget.nextPageContents(e, page, cur);									
				}else {
					retVal = jQuery.NestedSortableWidget.nextPageContents(e, page, e.nestedSortWidgetCfg.currentPage);				
				}
				jQuery.each(
					e.nestedSortWidgetCfg.loadedJsons,
				 	function(i) {
						if( this.requestFirstIndex <= retVal.firstIndex && (this.firstIndex + this.count) >= (retVal.firstIndex + retVal.count) ) 
						{
							retVal = null; //the whole thing is already there, don't fetch
							return false; //no need to keep looking
						}
					}
				);
				return retVal;
			} else if (e.nestedSortWidgetCfg.loadedJsons.length === 0) {
				//no pagination and nothing requested yet
				return {}; //the server should return everything
			} else {
				//no pagination and something requested
				//request nothing
				return null;
			}
		};
		/*
		 * Callback that gets called after loading data from the server.
		 */
		var process = function(json) {
			
			var tempProg = e.nestedSortWidgetCfg.tempProgress;
			if(tempProg) {
				//the first time we load the data
				
				//we need to remove the temporary progress indicator
				e.nestedSortWidgetCfg.tempProgress = null;
				tempProg.remove();
				
				//we call onInitialLoad callback
				if(e.nestedSortWidgetCfg.onInitialLoad) {
					e.nestedSortWidgetCfg.onInitialLoad.apply(e);	
				}
			}
			jQuery.NestedSortableWidget.augmentJson(e, json);
			jQuery.NestedSortableWidget.buildAndShowList(e, page);
			if(e.nestedSortWidgetCfg.onLoad) {
				e.nestedSortWidgetCfg.onLoad.apply(e);	
			}
			
			//hides the progress indicator
			jQuery.NestedSortableWidget.setBusyState(e, false);
			
		};
		/*
		 * Callback that gets called when there is an error.
		 */
		var reportFailure = function(a, b, c) {
			jQuery.NestedSortableWidget.userWarning(e, e.nestedSortWidgetCfg.text.loadError);
			//hides the progress indicator
			jQuery.NestedSortableWidget.setBusyState(e, false);
			if(e.nestedSortWidgetCfg.onLoadError) {
				e.nestedSortWidgetCfg.onLoadError.apply(e);	
			}
		};
		
		/*
		 * ACTUAL CODE
		 */
		
		if(
			e.nestedSortWidgetCfg.busyLoading ||
			e.nestedSortWidgetCfg.busyAnimating
		) {
			//gives up if something is being loaded/animated
			return false;
		}
		//signals the user there is something going on
		jQuery.NestedSortableWidget.setBusyState(e, true);
			
		//figures out what needs to be fetched from the server
		var itemsToRequest; 
		if (!e.nestedSortWidgetCfg.builtLists.sorts[page] && (itemsToRequest = whatToRequest()) !== null) {
			if(e.nestedSortWidgetCfg.loadUrlParams) {
				jQuery.extend(
					itemsToRequest,
					e.nestedSortWidgetCfg.loadUrlParams
				);				
			}

			// fetches the data 
			jQuery.ajax(
				{
					type: e.nestedSortWidgetCfg.loadRequestType,
					data: itemsToRequest,
					dataType : 'json',
					success: process,
					error: reportFailure,
					url: e.nestedSortWidgetCfg.loadUrl 
				}
			);
		} else {
			// or displays it from the cache
			jQuery.NestedSortableWidget.buildAndShowList(e, page);
			//hides the progress indicator
			jQuery.NestedSortableWidget.setBusyState(e, false);
		}

	},
	/*
	 * Determines what items "should" be displayed in the next page.
	 * Sometimes the first few elements requested will be skipped/won't be returned, 
	 * since each page should start with a root element.
	 */
	nextPageContents: function(e, nextPage, curPage) {
		var itemsPerPage = e.nestedSortWidgetCfg.itemsPerPage;
		var firstIndex, count;

		if(curPage){
			curFirstIndex = e.nestedSortWidgetCfg.builtLists.jsons[curPage].firstIndex;
			curCount = e.nestedSortWidgetCfg.builtLists.jsons[curPage].count;
			if(curPage + 1 == nextPage) {
				//current page right before the next one
				firstIndex = curFirstIndex + curCount ;
			} else if(curPage == nextPage + 1) {
				//current page right after the next one
				firstIndex = (nextPage-1)*itemsPerPage;
				if(firstIndex < 0) {
					firstIndex = 0;
				}
				count = curFirstIndex - firstIndex;
			}
		} else {
			firstIndex = (nextPage - 1) * itemsPerPage;
		}

		if(!count) {
			if(e.nestedSortWidgetCfg.loadedJsons[0]) {
				var total = e.nestedSortWidgetCfg.loadedJsons[0].totalCount;
				if(firstIndex + itemsPerPage > total) {
					//we are going to display the last page
					count = total - firstIndex;
				} else {
					//we are going to display a middle page
					count = itemsPerPage;
				}
			} else {
				count = itemsPerPage;
			}
		}
		
		return {firstIndex:firstIndex, count:count};
	},
	augmentJson : function(e, newJson) {
		
		var beforeIndex = null;
		var afterIndex = null;
		var insertPos = 0;
		
		//finds out where in which cluster to put the new json data
		jQuery.each(
			e.nestedSortWidgetCfg.loadedJsons,
		 	function(i) {
				if(newJson.firstIndex == this.firstIndex + this.count) {
					//existing cluster right before the new one
					beforeIndex = i;
				} else if (newJson.firstIndex + newJson.count == this.firstIndex){
					//existing cluster right after the new one
					afterIndex = i;
				} else if (newJson.firstIndex > this.firstIndex) {
					//otherwise records an inserction point for the new json cluster in the array
					insertPos = i + 1;
				}
			}	
		);
		
		if (beforeIndex !== null) {
			//appends the new json to an existing cluster
			e.nestedSortWidgetCfg.loadedJsons[beforeIndex].items = 
				e.nestedSortWidgetCfg.loadedJsons[beforeIndex].items.concat(newJson.items);
			e.nestedSortWidgetCfg.loadedJsons[beforeIndex].count += newJson.count;
			
			if(afterIndex !== null) {
				//the json we are inserting fits exactly in betweeen two adjancent clusters
				e.nestedSortWidgetCfg.loadedJsons[beforeIndex].items = 
					e.nestedSortWidgetCfg.loadedJsons[beforeIndex].items.concat(e.nestedSortWidgetCfg.loadedJsons[afterIndex].items);
				e.nestedSortWidgetCfg.loadedJsons[beforeIndex].count += e.nestedSortWidgetCfg.loadedJsons[afterIndex].count;
				e.nestedSortWidgetCfg.loadedJsons.splice(afterIndex, 1);
			}
		} else if (afterIndex !== null) {
			//prepends the new json to an existing cluster
			e.nestedSortWidgetCfg.loadedJsons[afterIndex].items =
				newJson.items.concat(e.nestedSortWidgetCfg.loadedJsons[afterIndex].items);
			e.nestedSortWidgetCfg.loadedJsons[afterIndex].firstIndex = newJson.firstIndex;
			e.nestedSortWidgetCfg.loadedJsons[afterIndex].requestFirstIndex = newJson.requestFirstIndex;
			e.nestedSortWidgetCfg.loadedJsons[afterIndex].count += newJson.count;
		} else {
			//we should just insert it as a new cluster
			e.nestedSortWidgetCfg.loadedJsons.splice(insertPos, 0, newJson);
		}
	},
	/*
	* Counts how many items, in the json representation, are decendants of this item.
	* If an array of elements is supplied, it sums the count for each element in the array
	*/
	countItems : function(element) {
		var retVar = 0;
		var a;
		if(element.constructor == Array) {
			a = element;
		} else {
			a = element.children;
		}
		
		if(a) {
			jQuery.each(
				a,
				function(i) {
					//counts this
					retVar ++; 
					
					//counts this' children
					retVar += jQuery.NestedSortableWidget.countItems(this);
				}
			);
		}
			
		return retVar;
	},
	/*
	 * Returns the subset of the appropriate element of e.nestedSortWidgetCfg.loadedJsons
	 * to be displayed for the current page
	 */
	jsonToDisplay: function(e, page, lastPage) {
		if(e.nestedSortWidgetCfg.paginate) {
			
			var jsons = e.nestedSortWidgetCfg.loadedJsons;				
					
			var itemsPerPage = e.nestedSortWidgetCfg.itemsPerPage;
			
			//what would you like to display?
			var contents;
			if(e.nestedSortWidgetCfg.incremental) {
				var insertPage;
				if(page > e.nestedSortWidgetCfg.upperPage) {
					insertPage = e.nestedSortWidgetCfg.upperPage;
				} else {
					insertPage = e.nestedSortWidgetCfg.bottomPage;
				}
				contents = jQuery.NestedSortableWidget.nextPageContents(e, page, insertPage);									
			}else {
				contents = jQuery.NestedSortableWidget.nextPageContents(e, page, lastPage);
			}
			var firstIndex = contents.firstIndex;
			var count = contents.count;
						
			//the superior boundary we cannot cross
			var maxIndex;
			var nextPageJson = e.nestedSortWidgetCfg.builtLists.jsons[page+1];
			if(nextPageJson) {
				//makes sure we don't repeat something that appears in the next page
				maxIndex = nextPageJson.firstIndex; //first element of next page
			} else {
				maxIndex = jsons[0].totalCount; //total number of items across all pages
			}
			
			var json = null; //the json cluster where the data is in
			//finds the cluster where the data is in
			jQuery.each(
				jsons,
				function(i) {
					if(this.requestFirstIndex <= firstIndex && (this.firstIndex + this.count) >= (firstIndex + count)) {
						json = this;
					} 
				}
			);
			
			//where are we inside the json cluster?
			var curPos = json.firstIndex;
			
			//what should be the first and last array indexes of this json to be displayed?
			var first = null;
			var last = null;
			
			//what is actually going to be displayed?
			var newFirstIndex = null;
			var newCount = null;
			
			//inside the clusters, gets the subset that will be displayed
			jQuery.each(
				json.items,
				function(i) {
					var nextPos = jQuery.NestedSortableWidget.countItems(this) + 1 + curPos;
					if(first === null && firstIndex <= curPos ) {
						//the first one in the cluster is the first to be displayed
						first = i;
						newFirstIndex = curPos;
					}
					if(first === null && nextPos > firstIndex ) {
						first = i + 1; //the first root element right after firstIndex is reached
						newFirstIndex = nextPos;
					}
					if(last === null && newFirstIndex!==null && (nextPos >= newFirstIndex + count || nextPos >= maxIndex ) ) {
						last = i; //the root element where the item with the last index is
						newCount = nextPos - newFirstIndex;
						return false; //we are done if we got here
					}
					curPos = nextPos;
				}
			);
			return {
				columns: json.columns, 
				items: json.items.slice(first, last + 1),
				firstIndex:newFirstIndex,
				count:newCount,
				totalCount: json.totalCount
			};
		} else {
			//no pagination
			//there should be only one json cluster
			return e.nestedSortWidgetCfg.loadedJsons[0];
		}
	},
	buildAndShowList:  function (e, page){
		
		/*
		 * PRIVATE FUNCTIONS
		 */
		
		/*
		 * Constructs the HTML element with the sortable list
		 */
		var buildListHtml = function (json, what) {
			/*
			 * PRIVATE FUNCTIONS
			 */
			var printItem = function (item) {
					var listToJoin = [];
					var id = "";
					//Cudos to M$. And some say open source is not trustable...
					var hackyStyleForCrappyIE = (jQuery.browser.msie) ? "style='ZOOM:1;FILTER: alpha(opacity=100);'" : "";
					if(item.id) {
						id = "id='" +  e.nestedSortWidgetCfg.classes.item + '-' + item.id + "' ";
					}
					listToJoin[listToJoin.length] = "<li "+ id + "class='"+e.nestedSortWidgetCfg.classes.clear+" "+e.nestedSortWidgetCfg.classes.item+"' "+hackyStyleForCrappyIE+"'>";
					var cursorStyle = "";
					if(!e.nestedSortWidgetCfg.handle) {
						cursorStyle = "cursor:move;";
					}
          //IE requires a height of 100%
          var heightForIE = (jQuery.browser.msie)?"height:100%;":"";
					listToJoin[listToJoin.length] = "<div class='"+e.nestedSortWidgetCfg.classes.itemRow+"' style='"+cursorStyle+" margin:0 0 " + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + e.nestedSortWidgetCfg.measureUnit + " 0; " + heightForIE +"'>";
					listToJoin[listToJoin.length] = printInfo(item.info, e.nestedSortWidgetCfg.handle);
					listToJoin[listToJoin.length] = "</div>";
					if(item.children) {
						listToJoin[listToJoin.length] = printItemList(item.children);
					}
					listToJoin[listToJoin.length] = "</li>";
					return listToJoin.join("");
				};
			
			var printItemList = function (itemListArray, isRoot) {
					var listToJoin = [];
					listToJoin[listToJoin.length] = "<ul " + ((isRoot) ? "id='" + e.nestedSortWidgetCfg.name + "-" + page + "'" : "") + "' class='"+e.nestedSortWidgetCfg.classes.listHolder+" "+e.nestedSortWidgetCfg.classes.clear+"'>";
					for(var i = 0; i < itemListArray.length ; i++){
						listToJoin[listToJoin.length] = printItem(itemListArray[i]);
					}
					listToJoin[listToJoin.length] = "</ul>";
					return listToJoin.join("");
				};
			
			var printInfo = function (columnsArray, withHandle) {
					var listToJoin = [];
					var unit = e.nestedSortWidgetCfg.measureUnit;
					var rtl = e.nestedSortWidgetCfg.nestedSortCfg.rightToLeft;
					
					for(var i = columnsArray.length - 1; i >= 0; i--){
						var style = "";
						if(i !== 0) {
							//colsWidth can be an array or a string
							var width;
							if(e.nestedSortWidgetCfg.colsWidth.constructor === Array) {
								width = (e.nestedSortWidgetCfg.colsWidth[i-1]) ? e.nestedSortWidgetCfg.colsWidth[i-1] : e.nestedSortWidgetCfg.colsWidth[e.nestedSortWidgetCfg.colsWidth.length - 1];
							} else {
								width = e.nestedSortWidgetCfg.colsWidth;
							}
							style += "width: " +  parseFloat(width) + unit + ";";
							
							if(rtl) {
								style += "float:left;";
								style += "margin:0 0 0 " + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + unit + ";";
							} else {
								style += "float:right;";
								style += "margin:0 " + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + unit + " 0 0;";
							}
							
						} else {
							
							if(rtl) {
								style += "margin:0 " + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + unit + " 0 " + firstColMargin + unit + ";";
							} else {
								style += "margin:0 " + firstColMargin + unit + " 0 " + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + unit + ";";
							}
						}
						
						//allows the user to define multi dimension padding
						var pad;
						if(e.nestedSortWidgetCfg.padding.constructor === Array) {
							pad = e.nestedSortWidgetCfg.padding.join(unit + " ") + unit;
						} else {
							pad = parseFloat(e.nestedSortWidgetCfg.padding) + unit;
						}
						style += "padding:" + pad + ";";
						
						listToJoin[listToJoin.length] = "<div style='"+style+"'>";
						if(withHandle && i === 0) {
							listToJoin[listToJoin.length] = "<span class='" + e.nestedSortWidgetCfg.classes.handle + "' style='cursor:move;'>" + e.nestedSortWidgetCfg.text.handle + "</span> ";
						}
						listToJoin[listToJoin.length] = columnsArray[i] +"</div>";
					}
					return listToJoin.join("");
				};
				
			var calcFirstColMargin = function(columnsArray) {
				var firstMargin = 0;
				
				//calculates the sum of the left and right padding
				var pad = e.nestedSortWidgetCfg.padding;
				var leftRightPad;
				if(pad.length === 4) {
					leftRightPad = parseFloat(pad[1]) + parseFloat(pad[3]);
				} else {
					leftRightPad = 2 * parseFloat(pad);
				}
			
				jQuery.each(
					columnsArray,
					function(i) {
						if(i === 0) {
							return true;
						}
						//colsWidth can be an array or a string.
						//If is is an array an has fewer elements the the columnsArray,
						//the last dimension will be repeated for the remaining elements.
						var colWidth;
						if(e.nestedSortWidgetCfg.colsWidth.constructor === Array) {
							colWidth = (e.nestedSortWidgetCfg.colsWidth[i-1]) ? e.nestedSortWidgetCfg.colsWidth[i-1] : e.nestedSortWidgetCfg.colsWidth[e.nestedSortWidgetCfg.colsWidth.length - 1];
						} else {
							colWidth = e.nestedSortWidgetCfg.colsWidth;
						}
						firstMargin += parseFloat(colWidth) + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + leftRightPad;
					}
				);
				
				//adds the margin for the first element
				return firstMargin + parseFloat(e.nestedSortWidgetCfg.whiteMargin);
			};
			
			/*
			 * Actual Code
			 */
			
			var listToJoin = [];
			
			var firstColMargin = calcFirstColMargin(json.columns);
			
			if(what === 'header') {
				if(json.columns) {
					listToJoin[listToJoin.length]="<div class='" + e.nestedSortWidgetCfg.classes.headerWrap + "'>";
					listToJoin[listToJoin.length] = "<ul class='"+ e.nestedSortWidgetCfg.classes.header +"'>";
					listToJoin[listToJoin.length] = "<li class='"+ e.nestedSortWidgetCfg.classes.headerItem +"'>";
					//IE requires a height of 100% to display it correctly
          var heightForIE = (jQuery.browser.msie)?"height:100%;":"";
          listToJoin[listToJoin.length] = "<div style='margin:0 0 " + parseFloat(e.nestedSortWidgetCfg.whiteMargin) + e.nestedSortWidgetCfg.measureUnit + " 0;" + heightForIE +" '>";
					listToJoin[listToJoin.length] = printInfo(json.columns);
					listToJoin[listToJoin.length] = "</div></li></ul>";
					listToJoin[listToJoin.length]="</div>";
				}
			} else {
				listToJoin[listToJoin.length] = printItemList(json.items, true);
			}
			
			return jQuery(listToJoin.join(""));
		};
		
		var buildListWrap = function() {
			return jQuery("<div class='" + e.nestedSortWidgetCfg.classes.listWrap + "'></div>");
		};
		
		/*
		 * Constructs the HTML element for the hovering boxes
		 */	
		var buildHoverBox = function(where) {
			if (e.nestedSortWidgetCfg.paginate) {
				var holder = '<div class="'+e.nestedSortWidgetCfg.classes.drop + ' '+e.nestedSortWidgetCfg.classes.clear + '"></div>';
				if (where == "before") {
					return jQuery(holder).html(e.nestedSortWidgetCfg.text.previousPageDrop);
				} else if (where == "after") {
					return jQuery(holder).html(e.nestedSortWidgetCfg.text.nextPageDrop);
				} else {
					return null;
				}
			} else {
				return null;
			}
		};
		
		
		/*
		 * Constructs the HTML element with next/previous page links.
		 */
		var buildPageChanger = function() {
			if (e.nestedSortWidgetCfg.paginate) {
				var classes = e.nestedSortWidgetCfg.classes;
				var text = e.nestedSortWidgetCfg.text;
				var prev = "", next= "";
				if(pageBefore) {
					prev = jQuery("<div class='"+classes.navPrevious+"'><a href='javascript:;'>"+text.previousItems+"</a></div>")
						.bind("click", function() {jQuery.NestedSortableWidget.loadPage(e, "before");});
				}
				if(pageAfter) {
					next = jQuery("<div class='"+classes.navNext+"'><a href='javascript:;'>"+text.nextItems+"</a></div>")
						.bind("click", function() {jQuery.NestedSortableWidget.loadPage(e, "after");});
				}
				return jQuery("<div class='"+classes.navLinks+"'></div>")
					.append(prev)
					.append(next)
					.append("<div style='clear:both;height:0;'>&nbsp;</div>");
			} else {
				return null;
			}
		};
		
		/*
		 * Builds the div that holds the save button and progress indicator.
		 */
		var buildSaveAndProgress = function () {
			var classes = e.nestedSortWidgetCfg.classes;
			var text = e.nestedSortWidgetCfg.text;
			var saveButton = jQuery("<input type='submit' class='"+classes.disabledSaveButton+"' value='"+text.saveButton+"'/>");
			return jQuery("<div class='"+classes.saveAndProgressWrap+"'></div>")
					.append("<div class='"+classes.progressAndWarningWrap+"'><div class='"+classes.warning+"' style='display:none;'>&nbsp;</div><div class='"+classes.progress+"' style='display:none;'>&nbsp;</div></div>")
					.append(saveButton)
					.append("<div style='clear:both;height:0;'>&nbsp;</div>");
		};
		
		
		var hideTransition = function(sortHide, showSort) {
			e.nestedSortWidgetCfg.busyAnimating = true;
			if(!e.nestedSortWidgetCfg.incremental) {
				if(typeof e.nestedSortWidgetCfg.transitionOut == 'function') {
					if(showSort) {
						e.nestedSortWidgetCfg.transitionOut.apply(
							sortHide, 
							[function() { showTransition(showSort); }]
						);
					} else {
						e.nestedSortWidgetCfg.transitionOut.apply(sortHide);
					}
				} else {
					sortHide.hide();
					if(showSort) {
						showTransition(showSort);
					}
				}
			}
		};
		
		var showTransition = function(sortableToShow) {
			if(typeof e.nestedSortWidgetCfg.transitionIn == 'function') {
				e.nestedSortWidgetCfg.transitionIn.apply(
					sortableToShow, 
					[
						function() {
							jQuery.recallDroppables();
							e.nestedSortWidgetCfg.busyAnimating = false;
						}
					]
				);						
			} else {
				sortableToShow.show();
				jQuery.recallDroppables();
				e.nestedSortWidgetCfg.busyAnimating = false;
			}
		};
		
		/*
		 * ACTUAL CODE
		 */

		var lastPage = e.nestedSortWidgetCfg.currentPage;
				
		//loads or builds the the list header
		var header = e.nestedSortWidgetCfg.header;
		var nothingBuiltYet = false; 	//flag that will be set if this is the first time
										//the list is being built
		if(!header) {
			nothingBuiltYet = true;
			header = e.nestedSortWidgetCfg.header = buildListHtml(e.nestedSortWidgetCfg.loadedJsons[0], 'header');
		}
		
		//loads or builds the div that wraps the list
		var listWrap = e.nestedSortWidgetCfg.listWrap;
		if(!listWrap) {
			listWrap = e.nestedSortWidgetCfg.listWrap = buildListWrap();
		}
		
		//loads the DOM element with the sortable for the current page
		var sort = e.nestedSortWidgetCfg.builtLists.sorts[page];
		var json = e.nestedSortWidgetCfg.builtLists.jsons[page];
		
		//if no list was built for this page, builds it now
		if (!sort) {
			//extracts the list to be built and saves
			json = e.nestedSortWidgetCfg.builtLists.jsons[page] = jQuery.NestedSortableWidget.jsonToDisplay(e, page, lastPage);
			
			//builds the list
			sort = e.nestedSortWidgetCfg.builtLists.sorts[page] = buildListHtml(json);
			
			if(listWrap.html() === "") {
				//if it is the first sort being built
				listWrap.append(sort);
			}
		}
		
		//determines whether or not the hover boxes should be displayed in this page
		if (e.nestedSortWidgetCfg.incremental) {
			json = e.nestedSortWidgetCfg.loadedJsons[0];
		}
		if(json.firstIndex > 0) {
			e.nestedSortWidgetCfg.builtLists.pageBefore[page] = true;
		} else {
			e.nestedSortWidgetCfg.builtLists.pageBefore[page] = false;
		}
		if (e.nestedSortWidgetCfg.incremental) {
			json = e.nestedSortWidgetCfg.loadedJsons[e.nestedSortWidgetCfg.loadedJsons.length-1];
		}
		if ( (json.firstIndex + json.count) < json.totalCount ) {
			e.nestedSortWidgetCfg.builtLists.pageAfter[page] = true;
		} else {
			e.nestedSortWidgetCfg.builtLists.pageAfter[page] = false;
		}
		
		//Hides the old sortable and inserts the new one at the right place
		var insertPage;
		if(e.nestedSortWidgetCfg.incremental) {
			if(page > e.nestedSortWidgetCfg.upperPage) {
				insertPage = e.nestedSortWidgetCfg.upperPage;
			} else {
				insertPage = e.nestedSortWidgetCfg.bottomPage;
			}									
		} else {
			insertPage = lastPage;
		}
		var lastSort = e.nestedSortWidgetCfg.builtLists.sorts[insertPage];
		if (lastSort) {
			if(insertPage < page) {
				lastSort.after(sort.hide());
			} else {
				lastSort.before(sort.hide());
			}
			//animates the transition
			switch(e.nestedSortWidgetCfg.transitionAnim) {
				case "custom-parallel":
					if(!e.nestedSortWidgetCfg.incremental) {
						hideTransition(lastSort);
					}
					showTransition(sort);
				break;
				case "custom-series":
					hideTransition(lastSort, sort);
				break;
			}		
		}
		
		//constructs the droppable DOM element to change to the previous page
		var hoverBefore = e.nestedSortWidgetCfg.hoverBefore;
		if(!hoverBefore) {
			hoverBefore = e.nestedSortWidgetCfg.hoverBefore = buildHoverBox('before');
		}

		//constructs the droppable DOM element to change to the next page
		var hoverAfter = e.nestedSortWidgetCfg.hoverAfter;
		if(!hoverAfter) {
			hoverAfter = e.nestedSortWidgetCfg.hoverAfter = buildHoverBox('after');
		}

		//shows or hides the droppables as required
		var pageBefore = e.nestedSortWidgetCfg.builtLists.pageBefore[page];
		if(hoverBefore) {
			if(pageBefore) {
				hoverBefore.show().css('opacity', '1');
				
			} else {
				hoverBefore.hide();
			}
		}

		var pageAfter = e.nestedSortWidgetCfg.builtLists.pageAfter[page];
		if(hoverAfter) {
			if (pageAfter) {
				hoverAfter.show().css('opacity', '1');
			} else {
				hoverAfter.hide();
			}
		}

		//removes the old page change from the document and inserts the new one
		var oldPageChanger = e.nestedSortWidgetCfg.pageChanger;
		//constructs/gets the DOM element with next/previous page links
		e.nestedSortWidgetCfg.pageChanger = buildPageChanger();
		var pageChanger = e.nestedSortWidgetCfg.pageChanger;
		if(oldPageChanger) {
			oldPageChanger.hide().after(pageChanger).remove();
		}
		
		//builds the div that holds the save button and progress indicator
		var savProg = e.nestedSortWidgetCfg.saveAndProgress;
		if(!savProg) {
			savProg = e.nestedSortWidgetCfg.saveAndProgress = [];
			savProg[0] = buildSaveAndProgress();
			savProg[1] = buildSaveAndProgress();
		}

		//puts everything together and appends the widget to the given element
		if(nothingBuiltYet){
			e.nestedSortWidgetCfg.divWrap
				.prepend(listWrap)
				.prepend(header)
				.prepend(hoverBefore)
				.append(hoverAfter)
				.prepend(pageChanger)
				.prepend(savProg[0])
				.append(savProg[1])
				.appendTo(e);	
		}

		//creates the droppables if is not already created
		if(hoverBefore && !hoverBefore.get(0).isDroppable) {
			hoverBefore.Droppable(
				{
					accept: e.nestedSortWidgetCfg.classes.item,
					tolerance: 'pointer',
					hoverclass: e.nestedSortWidgetCfg.classes.activeDrop,
					onHover: function(drag) {jQuery.NestedSortableWidget.onBoxHover(e, drag, "before", this);},
					onOut: function (drag) {jQuery.NestedSortableWidget.onBoxOutOrDrop(e, drag, "before", this);},
					onDrop: function (drag) {jQuery.NestedSortableWidget.onBoxOutOrDrop(e, drag, "before", this);}
				}
			);
		}
		if(hoverAfter && !hoverAfter.get(0).isDroppable) {
			hoverAfter.Droppable(
				{
					accept: e.nestedSortWidgetCfg.classes.item,
					tolerance: 'pointer',
					hoverclass: e.nestedSortWidgetCfg.classes.activeDrop,
					onHover: function(drag) {jQuery.NestedSortableWidget.onBoxHover(e, drag, "after", this);},
					onOut: function (drag) {jQuery.NestedSortableWidget.onBoxOutOrDrop(e, drag, "after", this);},
					onDrop: function (drag) {jQuery.NestedSortableWidget.onBoxOutOrDrop(e, drag, "after", this);}
				}
			);
		}

		//creates the nestedsortable if not already created
		var sortId;
		if(!sort.get(0).isNestedSortable) {
			sortId = sort.attr('id');
			e.nestedSortWidgetCfg.builtLists.indexFromSortId[sortId] = page;
			sort.NestedSortable(
				e.nestedSortWidgetCfg.nestedSortCfg
			);	
		}
		
		//if moving from one page to the other
		if(lastSort) {
			//places the helper on the top of the NestedSortable list
			jQuery.iNestedSortable.insertOnTop(sort.get(0));
		}

		// Saves lastPage (the last one displayed), currentPage bottomPage (the one with the lowest index)
		// and upperPage (the one with the biggest index)
		e.nestedSortWidgetCfg.lastPage = lastPage;
		e.nestedSortWidgetCfg.currentPage = page;
		if(!e.nestedSortWidgetCfg.upperPage || page > e.nestedSortWidgetCfg.upperPage) {
			e.nestedSortWidgetCfg.upperPage = page;
		}
		if(!e.nestedSortWidgetCfg.bottomPage || page < e.nestedSortWidgetCfg.bottomPage) {
			e.nestedSortWidgetCfg.bottomPage = page;
		}
		
		//remeasures the droppables and sortable
		jQuery.recallDroppables();

		//makes rows alternate CSS classes
		jQuery.NestedSortableWidget.alternateClasses(e);
	},
	onListChange: function (e, ser) {
		//makes rows alternate CSS classes
		jQuery.NestedSortableWidget.alternateClasses(e);
		
		//The ser param is an array containing the serialization for all
		//the nestedsortables that were changed. We have to iterate over this array.
		jQuery.each(
			ser,
			function (i) {
				//saves serialized output for each modified page
				var index = e.nestedSortWidgetCfg.builtLists.indexFromSortId[this.id];
				e.nestedSortWidgetCfg.builtLists.sers[index] = this.o[this.id];
			}
		);
		
		//Enables the save button
		jQuery("." + e.nestedSortWidgetCfg.classes.disabledSaveButton, e)
			.click(
					function(event){
						jQuery(e).NestedSortableWidgetSave();
						event.preventDefault();
					}
				)
			.addClass(e.nestedSortWidgetCfg.classes.saveButton)
			.removeClass(e.nestedSortWidgetCfg.classes.disabledSaveButton);
			
	},
	onBoxHover: function(e, drag, where, drop) {
		callback = function() {		
			jQuery.NestedSortableWidget.loadPage(e, where);
		};
		var changeTime = e.nestedSortWidgetCfg.pageChangeTimer;
		if(e.nestedSortWidgetCfg.fadeOutHover && jQuery.fn.jquery !== "1.2") {
			//Interface 1.2 has problems with jQuery 1.2, in the animations. 
			//Until it is fixed, fadeOut hover won't work (we can't stop it).
			var animHideCfg = {};
			animHideCfg[e.nestedSortWidgetCfg.fadeOutProperty] = 'hide';
			jQuery(drop).animate({opacity:'0'}, parseInt(changeTime, 10), callback);
		} else {
			e.nestedSortWidgetCfg.lastTimeOut = setTimeout(callback, changeTime + "");
		}
		
	},
	onBoxOutOrDrop: function(e, drag, where, drop) {
		if(e.nestedSortWidgetCfg.fadeOutHover&& jQuery.fn.jquery !== "1.2") {
			//Interface 1.2 has problems with jQuery 1.2, in the animations. 
			//Until it is fixed, fadeOut hover won't work (we can't stop it).
			jQuery(drop).stop().css('opacity', '1');
		} else {
			clearTimeout(e.nestedSortWidgetCfg.lastTimeOut);
		}
	},
	alternateClasses: function(e) {
		jQuery('div.' + e.nestedSortWidgetCfg.classes.itemRow + ':odd', e)
			.find('div')
			.addClass(e.nestedSortWidgetCfg.classes.altCell);
		jQuery('div.' + e.nestedSortWidgetCfg.classes.itemRow + ':even', e)
			.find('div')
			.removeClass(e.nestedSortWidgetCfg.classes.altCell);
	},
	save: function() {
			
		var onSuccess = function(e, returnText) {
			jQuery.NestedSortableWidget.userWarning(e, e.nestedSortWidgetCfg.text.saveMessage);
			
			if(e.nestedSortWidgetCfg.onSave) {
				e.nestedSortWidgetCfg.onSave.apply(e, [returnText]);	
			}
		};
		
		var onError = function(e) {
			jQuery.NestedSortableWidget.userWarning(e, e.nestedSortWidgetCfg.text.saveError);
			
			if(e.nestedSortWidgetCfg.onSaveError) {
				e.nestedSortWidgetCfg.onSaveError.apply(e, [returnText]);	
			}
		};
		
		var onBoth = function(e) {
			jQuery.NestedSortableWidget.setBusyState(e, false);
		};
		
		return this.each( function() {
			if(this.isNestedSortableWidget) {
				//The idea here is to gather the serialization 
				//generated for each page into a unified array.
				
				//If we have separate blocks of modified pages 
				//(eg. only page 1, 2, 5 and 6 were changed), more than a one unified
				// block would be generated.
				
				if(this.nestedSortWidgetCfg.busyLoading || this.nestedSortWidgetCfg.builtLists.sers.length === 0) {
					//gives up if something is being loaded
					//or if nothing was changed yet
					return false;
				}
				
				jQuery.NestedSortableWidget.setBusyState(this, true);
				
				var jsonSer = []; //the array with all serialization blocks
				var currentJsonSer; //the current serialization block
				var lastIndex;
				var that = this;
				jQuery.each(
					that.nestedSortWidgetCfg.builtLists.sers,
					function(i) {
						
						//skips the one with index 0
						if(!that.nestedSortWidgetCfg.builtLists.sers[i]) {
							return true;
						}
						
						var serObj = this;
						
						if( currentJsonSer && lastIndex && (lastIndex + 1 == i) ) {
							//if there was a serialized page right before this
							currentJsonSer.items = currentJsonSer.items.concat(serObj);
							currentJsonSer.count += jQuery.NestedSortableWidget.countItems(serObj);
						} else {
							
							currentJsonSer = jsonSer[jsonSer.length] = 
								{
									firstIndex:that.nestedSortWidgetCfg.builtLists.jsons[i].firstIndex, 
									count: jQuery.NestedSortableWidget.countItems(serObj), 
									items: serObj
								};
						}

						lastIndex = i;
					}
				);
				
				//if sendObj one was one block we will send it as a single element, not an array
				var sendObj = (jsonSer.length) > 1 ? jsonSer : jsonSer[0];
				
				var sendString;
				if(jQuery.toJSON && that.nestedSortWidgetCfg.serializeWithJSON) {
					//json serialization
					sendString = {};
					sendString[that.nestedSortWidgetCfg.name] = jQuery.toJSON(sendObj);
					if(that.nestedSortWidgetCfg.saveUrlParams){
						jQuery.extend(sendString, that.nestedSortWidgetCfg.saveUrlParams);
					}
				} else {
					sendString = "";
					if(that.nestedSortWidgetCfg.saveUrlParams) {
						jQuery.each(
							that.nestedSortWidgetCfg.saveUrlParams,
							function(key) {
								if(sendString.length > 0) {
									sendString += "&";
								}
								sendString += key + "=" + this;
							}
						);
					}

					//recursive function that creates a query string
					//based on the JavaScript object
					var buildQueryString = function(arrayObject, currentPath){
						var retQuery = "";
						jQuery.each(
							arrayObject,
							function(i) {
								if(retQuery.length > 0) {
									retQuery += '&';
								}
								retQuery += currentPath + '['+i+'][id]=' + this.id;
								if(this.children && this.children.constructor == Array) {
									retQuery += "&" + buildQueryString(this.children, currentPath + '['+i+'][children]');
								}
							}
						);	
						return retQuery;
					};
					
					if(sendObj.constructor == Array) {
						jQuery.each(
							sendObj,
							function(i) {
								if(sendString.length > 0) {
									sendString += "&";
								}
								sendString += that.nestedSortWidgetCfg.name + "["+i+"][count]=" + this.count + "&" + that.nestedSortWidgetCfg.name + "["+i+"][firstIndex]=" + this.firstIndex + "&";
								sendString += buildQueryString(this.items, that.nestedSortWidgetCfg.name + "["+i+"][items]");

							}
						);
					} else {
						if(sendString.length > 0) {
							sendString += "&";
						}
						sendString += that.nestedSortWidgetCfg.name + "[count]=" + sendObj.count + "&" + that.nestedSortWidgetCfg.name + "[firstIndex]=" + sendObj.firstIndex + "&";
						sendString += buildQueryString(sendObj.items, that.nestedSortWidgetCfg.name + "[items]");
					}
				}
				
				jQuery.ajax({
					url: that.nestedSortWidgetCfg.saveUrl,
					type: that.nestedSortWidgetCfg.saveRequestType,
					data: sendString,
					success: function(ret) {onSuccess(that, ret);},
					error: function(xml, error, ex) {onError(that);},
					complete: function(xml, status) {onBoth(that);} 
				});
			}
		});
	},
	destroy : function() {
		return this.each(function() {
			if(this.isNestedSortableWidget) {
				var callback = this.nestedSortWidgetCfg.onDestroy;
				jQuery.each(
					this.nestedSortWidgetCfg.builtLists.sorts,
					function(i) {
						if(this) {
							jQuery(this).NestedSortableDestroy();
						}
					}
				);
				if(this.nestedSortWidgetCfg.hoverBefore) {
					this.nestedSortWidgetCfg.hoverBefore.DroppableDestroy();
				}
				if(this.nestedSortWidgetCfg.hoverAfter) {
					this.nestedSortWidgetCfg.hoverAfter.DroppableDestroy();
				}
				
				this.nestedSortWidgetCfg = null;
				this.isNestedSortableWidget = false;
				jQuery(this).html('');
				if(callback) {
					callback.apply(this);
				}
			}
		});
	},
	build: function(conf) {
		return this.each(
			function() {
				if(this.isNestedSortableWidget ||
					!conf.loadUrl ||
				 	!jQuery.iUtil ||
				  	!jQuery.iDrag ||
				  	!jQuery.iDrop ||
				    !jQuery.iSort ||
					!jQuery.iNestedSortable) {
						return;
					}

				var that = this;
				this.isNestedSortableWidget = true;
				this.nestedSortWidgetCfg = {
					name : conf.name ? conf.name : "nested-sortable-widget",
					loadUrl : conf.loadUrl,
					saveUrl : conf.saveUrl ? conf.saveUrl : conf.loadUrl,
					loadUrlParams: conf.loadUrlParams ? conf.loadUrlParams : undefined,
					saveUrlParams: conf.saveUrlParams ? conf.saveUrlParams : undefined,
					loadRequestType: conf.loadRequestType ? conf.loadRequestType : 'GET',
					saveRequestType: conf.saveRequestType ? conf.saveRequestType : 'POST',
					serializeWithJSON : conf.serializeWithJSON === undefined ? false : conf.serializeWithJSON,
					onLoad : (conf.onLoad && conf.onLoad.constructor == Function) ? conf.onLoad :false,
					onLoadError : (conf.onLoadError && conf.onLoadError.constructor == Function) ? conf.onLoadError :false,
					onInitialLoad : (conf.onInitialLoad && conf.onInitialLoad.constructor == Function) ? conf.onInitialLoad : false,
					onSave : (conf.onSave && conf.onSave.constructor == Function) ? conf.onSave :false,
					onSaveError : (conf.onSaveError && conf.onSaveError.constructor == Function) ? conf.onSaveError :false,
					onDestroy : (conf.onDestroy && conf.onDestroy.constructor == Function) ? conf.onDestroy :false,
					nestedSortCfg : conf.nestedSortCfg ? conf.nestedSortCfg : {},
					loadButtonSel : conf.loadButtonSel ? conf.loadButtonSel :false,
					colsWidth: conf.colsWidth ? conf.colsWidth : 150,
					whiteMargin: conf.whiteMargin ? conf.whiteMargin : 2,
					padding: conf.padding ? conf.padding : 4,
					measureUnit: conf.measureUnit ? conf.measureUnit : "px",
					handle: conf.handle ? conf.handle : false,
										
					//configuration that only matters when pagination is on
					paginate : conf.paginate ? true : false,
					greedy : conf.greedy ? true : false,
					incremental: conf.incremental ? conf.incremental : false,
					itemsPerPage : parseInt(conf.itemsPerPage, 10) || 10,
					startPage : parseInt(conf.startPage, 10) || 1,
					pageChangeTimer : conf.pageChangeTimer ? conf.pageChangeTimer : "500",
					fadeOutHover: conf.fadeOutHover ? conf.fadeOutHover : true,
					fadeOutProperty: conf.fadeOutProperty ? conf.fadeOutProperty : 'opacity',
					transitionAnim: conf.transitionAnim ? conf.transitionAnim : 'slide-parallel',
					transitionOut: typeof conf.transitionOut =='function' ? conf.transitionOut : false,
					transitionIn: typeof conf.transitionIn =='function' ? conf.transitionIn : false
				};
				
				//css classes for generated elements
				this.nestedSortWidgetCfg.classes = {
					listWrap : 'nsw-list-wrap',
					headerWrap : 'nsw-header-wrap',
					wrap: 'nsw-wrap',
					drop: 'nsw-drop',
					activeDrop: 'nsw-active-drop',
					navLinks: 'nsw-nav-links',
					navPrevious: 'nsw-nav-previous',
					navNext: 'nsw-nav-next',
					listHolder: 'nsw-list-holder',
					header: 'nsw-header',
					headerItem: 'nsw-header-item',
					clear: 'nsw-clear',
					item: 'nsw-item',
					altCell: 'nsw-alt-cell',
					itemRow: 'nsw-item-row',
					progress: 'nsw-progress',
					saveButton: 'nsw-save-button',
					disabledSaveButton: 'nsw-disabled-save-button',
					saveAndProgressWrap: 'nsw-save-progress-wrap',
					progressAndWarningWrap: 'nsw-progress-warning-wrap',
					warning: 'nsw-warning',
					handle: 'nsw-handle',
					helper: 'nsw-helper'
				};
				
				//configures user defined class names
				if(conf.classes) {
					jQuery.extend(this.nestedSortWidgetCfg.classes, conf.classes);
				}
				
				//Text used in the widget
				this.nestedSortWidgetCfg.text = {
					nextPageDrop: "Hover the mouse here when dragging to place the item in the next page.",
					previousPageDrop: "Hover the mouse here when dragging to place the item in the previous page.",
					nextItems: "Next Entries &raquo;",
					previousItems: "&laquo; Previous Entries",
					saveButton: "Save Order &raquo; ",
					loadError: "Could not load the data from the server.",
					saveError: "Could not send the data to the server.",
					saveMessage: "Data successfully saved.",
					handle: "[drag]"
				};
				
				//Configures user defined text
				if(conf.text) {
					jQuery.extend(this.nestedSortWidgetCfg.text, conf.text);
				}
								
				//adds cfg to the nestedsortable
				this.nestedSortWidgetCfg.nestedSortCfg.accept = this.nestedSortWidgetCfg.classes.item;
				
				//adds an onchange callback
				var userOnChange = this.nestedSortWidgetCfg.nestedSortCfg.onChange;
				this.nestedSortWidgetCfg.nestedSortCfg.onChange = function(ser) {
					if(userOnChange){userOnChange(ser);}
					jQuery.NestedSortableWidget.onListChange(that, ser);
				};
				
				//Sets up the helper class for the sortable
				this.nestedSortWidgetCfg.nestedSortCfg.helperclass = this.nestedSortWidgetCfg.classes.helper;
				
				//Sets up the drag handle for the sortable
				if(this.nestedSortWidgetCfg.handle) {
					this.nestedSortWidgetCfg.nestedSortCfg.handle = "." + this.nestedSortWidgetCfg.classes.handle;
				} else {
					this.nestedSortWidgetCfg.nestedSortCfg.handle = "." + this.nestedSortWidgetCfg.classes.itemRow;
				}
				
				//div that wraps everything
				this.nestedSortWidgetCfg.divWrap = jQuery("<div class='"+ this.nestedSortWidgetCfg.classes.wrap +"'></div>");
				
				//holds the data that has been loaded from the server
				this.nestedSortWidgetCfg.loadedJsons = [];
				
				//holds information for each page, as they are built
				this.nestedSortWidgetCfg.builtLists = {
					sorts:[], 
					jsons:[], 
					sers:[], 
					pageBefore:[], //booleans
					pageAfter:[], //booleans
					pageChangers: [],
					indexFromSortId: {}
				};
				
				//adds some html to allow the user to see load error messages 
				//and the progress indicator before loading the first page.
				this.nestedSortWidgetCfg.tempProgress = jQuery("<div class='"+this.nestedSortWidgetCfg.classes.saveAndProgressWrap+"'></div>")
					.append("<div class='"+this.nestedSortWidgetCfg.classes.progressAndWarningWrap+"'><div class='"+this.nestedSortWidgetCfg.classes.warning+"' style='display:none;'>&nbsp;</div><div class='"+this.nestedSortWidgetCfg.classes.progress+"' style='display:none;'>&nbsp;</div></div>")
					.append("<div style='clear:both;height:0;'>&nbsp;</div>")
					.appendTo(this);
				
				//Sets up page transition animation
				switch(this.nestedSortWidgetCfg.transitionAnim) {
					case "slide-parallel":
						this.nestedSortWidgetCfg.transitionOut = function(call){jQuery.fn.slideUp.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionIn = function(call){jQuery.fn.slideDown.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionAnim = "custom-parallel";
					break;
					case "slide-series":
						this.nestedSortWidgetCfg.transitionOut = function(call){jQuery.fn.slideUp.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionIn = function(call){jQuery.fn.slideDown.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionAnim = "custom-series";
					break;
					case "fade-series":
						this.nestedSortWidgetCfg.transitionOut = function(callback){this.fadeOut("fast", callback );};
						this.nestedSortWidgetCfg.transitionIn = function(callback){this.fadeIn("fast", callback );};
						this.nestedSortWidgetCfg.transitionAnim = "custom-series";
					break;
					case "normal-parallel":
						this.nestedSortWidgetCfg.transitionOut = function(call){jQuery.fn.hide.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionIn = function(call){jQuery.fn.show.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionAnim = "custom-parallel";
					break;
					case "normal-series":
						this.nestedSortWidgetCfg.transitionOut = function(call){jQuery.fn.hide.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionIn = function(call){jQuery.fn.show.apply(this,["normal", call]);};
						this.nestedSortWidgetCfg.transitionAnim = "custom-series";
					break;
					case "custom-series":
					case "custom-parallel":
						//leave as is, so the user can configure things himself
					break;
					case "none":
					default:
						//no animation
						this.nestedSortWidgetCfg.transitionOut = false;
						this.nestedSortWidgetCfg.transitionIn = false;
						this.nestedSortWidgetCfg.transitionAnim = "custom-parallel";
					break;
				}		

				
				//sets up the load buttom or loads the stuff right now
				if(this.nestedSortWidgetCfg.loadButtonSel) {
					jQuery(this.nestedSortWidgetCfg.loadButtonSel)
						.click(function(){jQuery.NestedSortableWidget.loadData(that, that.nestedSortWidgetCfg.startPage);});
				} else {
					jQuery.NestedSortableWidget.loadData(this, this.nestedSortWidgetCfg.startPage);
				}
			}
		);
	}
	
};

//Extends jQuery to add the plugin.
jQuery.fn.extend(
	{
		NestedSortableWidget : jQuery.NestedSortableWidget.build,
		NestedSortableWidgetSave : jQuery.NestedSortableWidget.save,
		NestedSortableWidgetDestroy: jQuery.NestedSortableWidget.destroy
	}
);



/*
 * There is a bug in the remeasure function in Interface's iDrop, 
 * which makes it give a javascript error. I submited a patch to 
 * fix it, but while it is not applied, we have to "monkey" patch it here.
 */
jQuery.iDrop.remeasure = jQuery.recallDroppables =  function()
	{
		jQuery.iDrop.highlighted = {};
		for (i in jQuery.iDrop.zones) {
			if (jQuery.iDrop.zones[i] != null) {
				var iEL = jQuery.iDrop.zones[i].get(0);
				if (jQuery(jQuery.iDrag.dragged).is('.' + iEL.dropCfg.a)) {
					iEL.dropCfg.p = jQuery.extend(
						jQuery.iUtil.getPosition(iEL),
						jQuery.iUtil.getSizeLite(iEL)
					);
					if (iEL.dropCfg.ac) {
						jQuery.iDrop.zones[i].addClass(iEL.dropCfg.ac);
					}
					jQuery.iDrop.highlighted[i] = jQuery.iDrop.zones[i];
					
					if (jQuery.iSort && iEL.dropCfg.s && jQuery.iDrag.dragged.dragCfg.so) {
						iEL.dropCfg.el = jQuery('.' + iEL.dropCfg.a, iEL);
						jQuery.iSort.measure(iEL);
					}
				}
			}
		}
	};
