#include "sdr.h"

 
 
 
 
extern void *serverthread(void *arg) {

    mqd_t mq;
    struct mq_attr attr;
    char buffer[MAX_SIZE + 1];

     
    attr.mq_flags = 0;
    attr.mq_maxmsg = 10;
    attr.mq_msgsize = MAX_SIZE;
    attr.mq_curmsgs = 0;

     
     
     
    int open_flags = 0;
    open_flags = O_CREAT | O_RDONLY | O_NONBLOCK;

     
    mq = mq_open(QUEUE_NAME, open_flags, 0644, &attr);
    CHECK((mqd_t) - 1 != mq);

     
    while (!sdrstat.stopflag) {
        ssize_t bytes_read;

         
        bytes_read = mq_receive(mq, buffer,
                                MAX_SIZE, NULL);

         
         

         
        if (bytes_read > 0) {
             
            buffer[bytes_read] = '\0';

             
             
            printf("%s",buffer);

             
             
            buffer[0] = '\0';
        }

    }

     
    printf("Received stopflag, stopping server thread\n");

     
     
     
    mq_close(mq);
    mq_unlink(QUEUE_NAME);

     
    printf("At server return\n");
    return 0;
}
