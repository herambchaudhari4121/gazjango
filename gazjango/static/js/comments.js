/*
    TODO: show links for new comments don't work
    TODO: when a comment is posted, highlight it
*/

var speed = 'normal';

function hideFunctionFor(id) {
  return function() {
    $('#c-' + id)
      .removeClass('shown-comment').addClass('hidden-comment')
      .find('.commentText').slideUp(speed).end()
      .find('.showLink')
        .html('show anyway')
        .unbind('click')
        .click(showFunctionFor(id));
    return false;
  };
}
function showFunctionFor(id) {
  return function() {
    $('#c-' + id)
      .removeClass('hidden-comment').addClass('shown-comment')
      .find('.commentText').slideDown(speed).end()
      .find('.showLink')
        .html('hide')
        .unbind('click')
        .click(hideFunctionFor(id));
    return false;
  };
}

function setupShowLinks() {
  $('.hidden-comment').each(function() {
    var comment = this;
    var id = comment.id.substring('2');
    
    $(comment)
      .find('.showLink')
        .unbind('click')
        .click(function(obj) {
            $(comment)
              .find('.commentText')
                .hide()
                .load('show-comment/' + id + '/', function() {
                    $(this).slideDown(speed);
                })
                .removeClass('hidden-comment').addClass('shown-comment')
                .end()
              .find('.showLink')
                .html('hide')
                .unbind('click')
                .click(hideFunctionFor(id));
          return false;
        });
  });
}

$(document).ready(setupShowLinks);


var default_comment_name;
$(document).ready(function() {
   default_comment_name = $('input[name="name"]').val();
});

function toggleNameDisabled() {
    namebox = $('input[name="name"]');
    if (namebox.attr('disabled')) {
        namebox.attr('disabled', false);
    } else {
        namebox.val(default_comment_name);
        namebox.attr('disabled', true);
    }
}

function refreshComments() {
    $('#comments').load('comments/', null, setupShowLinks);
}

function newComments() {
    comments = $('.comment');
    if (comments.length == 0) {
        last_num = 0;
    } else {
        last_num = comments.get(comments.length - 1).id.substr(2);
    }
    $.get('comments/' + last_num + '/', {}, function(data, textStatus) {
        $('#comments').append(data);
        setupShowLinks();
        
        var new_comments = $('.comment.new');
        var i = 0;
        callback = function() {
            i++;
            if (i < new_comments.length) {
                new_comments.eq(i).slideDown('normal', callback).removeClass('new');
            }
        }        
        new_comments.eq(0).slideDown('normal', callback);
    });
}


function submitComment() {
    data = {};
    $('#commentForm :input').each(function() {
        data[$(this).attr('name')] = $(this).val();
    });
    
    $.post($('#commentForm form').attr('action'), data,
       function(resp, textStatus) {
           if (resp == 'success') {
               newComments();
               $('#commentForm input[type=reset]').click();
           } else {
               // it's okay to kill the <h4>, since it's unlikely that
               // many people will have javascript on but css off :)
               $('#commentForm').html(resp);
           }
       }
    );
    return false;
}